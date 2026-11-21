import hashlib
import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from xml.dom import minidom

from pydantic import BaseModel

from app.core.config import settings

if TYPE_CHECKING:
    from app.models.schemas import AuditResult


class CargoWiseShipmentData(BaseModel):
    shipment_id: str = "S00001000"
    declaration_id: str = "B00001000"
    port_origin_code: str = "ZADUR"
    port_origin_name: str = "Durban"
    port_dest_code: str = "NLRTM"
    port_dest_name: str = "Rotterdam"
    invoice_number: str = "CI-2026-01"
    incoterm: str = "CIF"
    invoice_amount: Decimal = Decimal("148500.00")
    insurance_amount: Decimal = Decimal("1450.00")

class CargoWiseExportService:
    """
    Generates CargoWise One UniversalShipment-style XML (namespace
    http://www.cargowise.com/Schemas/Universal/2011/11, version 1.1).
    Validated only against the structural-subset XSD kept in this repo, not against
    WiseTech-published schemas, and not transmitted anywhere (no eAdaptor transport).
    Enforces deterministic Python Decimal arithmetic with zero floating-point drift.
    """

    def generate_universal_interchange_xml(
        self,
        shipment_id: str = "S00001000",
        declaration_id: str = "B00001000",
        port_origin_code: str = "ZADUR",
        port_origin_name: str = "Durban",
        port_dest_code: str = "NLRTM",
        port_dest_name: str = "Rotterdam",
        consignor_code: str = "TSTORGCHC",
        invoice_number: str = "CI-2026-01",
        incoterm: str = "CIF",
        invoice_amount: Decimal = Decimal("148500.00"),
        insurance_amount: Decimal = Decimal("1450.00"),
        line_items: Optional[List[Dict[str, Any]]] = None,
        audit_status: str = "CLEARED_WITH_RECONCILIATION",
        penalty_status: str = "19_USC_1592_PROTECTED",
        company_code: Optional[str] = None,
        enterprise_id: Optional[str] = None,
        server_id: Optional[str] = None,
    ) -> str:
        if line_items is None:
            line_items = [
                {
                    "line_number": 1,
                    "description": "Industrial Controller Assembly with Integrated Circuitry",
                    "hts_code": "8542.31",
                    "value": Decimal("149950.00")
                }
            ]

        # Corridor jurisdiction check:
        # 19 U.S.C. § 1592 only applies to US import corridors (destination in US e.g. USLAX).
        # Non-US destinations (e.g. NLRTM Rotterdam in the EU) are subject to EU UCC, not US CBP penalties.
        # Never flag 19_USC_1592_PROTECTED on non-US shipments.
        is_us_corridor = port_dest_code.upper().startswith("US")
        if not is_us_corridor and penalty_status == "19_USC_1592_PROTECTED":
            penalty_status = "EU_UCC_COMPLIANT"

        # Root UniversalInterchange Envelope
        root = ET.Element(
            "UniversalInterchange",
            xmlns="http://www.cargowise.com/Schemas/Universal/2011/11",
            version="1.1"
        )

        # Content-addressed CorrelationID
        corr_seed = f"{shipment_id}:{declaration_id}:{port_origin_code}:{port_dest_code}:{invoice_amount}"
        correlation_id = f"CW-{hashlib.sha256(corr_seed.encode('utf-8')).hexdigest()[:16].upper()}"

        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "SenderID").text = settings.CARGOWISE_SENDER_ID
        ET.SubElement(header, "RecipientID").text = settings.CARGOWISE_RECIPIENT_ID
        ET.SubElement(header, "CorrelationID").text = correlation_id

        body = ET.SubElement(root, "Body")
        universal_shipment = ET.SubElement(
            body,
            "UniversalShipment",
            xmlns="http://www.cargowise.com/Schemas/Universal/2011/11",
            version="1.1"
        )

        shipment = ET.SubElement(universal_shipment, "Shipment")

        # Routing & Context
        data_context = ET.SubElement(shipment, "DataContext")
        data_target_collection = ET.SubElement(data_context, "DataTargetCollection")
        
        target_fwd = ET.SubElement(data_target_collection, "DataTarget")
        ET.SubElement(target_fwd, "Type").text = "ForwardingShipment"
        ET.SubElement(target_fwd, "Key").text = shipment_id

        target_cus = ET.SubElement(data_target_collection, "DataTarget")
        ET.SubElement(target_cus, "Type").text = "CustomsDeclaration"
        ET.SubElement(target_cus, "Key").text = declaration_id

        effective_company = company_code or getattr(settings, "CARGOWISE_COMPANY_CODE", "CPH")
        effective_enterprise = enterprise_id or getattr(settings, "CARGOWISE_ENTERPRISE_ID", "TRN")
        effective_server = server_id or getattr(settings, "CARGOWISE_SERVER_ID", "A04")

        company = ET.SubElement(data_context, "Company")
        ET.SubElement(company, "Code").text = effective_company
        ET.SubElement(data_context, "EnterpriseID").text = effective_enterprise
        ET.SubElement(data_context, "ServerID").text = effective_server

        # Ports
        port_origin = ET.SubElement(shipment, "PortOfOrigin")
        ET.SubElement(port_origin, "Code").text = port_origin_code
        ET.SubElement(port_origin, "Name").text = port_origin_name

        port_dest = ET.SubElement(shipment, "PortOfDestination")
        ET.SubElement(port_dest, "Code").text = port_dest_code
        ET.SubElement(port_dest, "Name").text = port_dest_name

        # Organization
        org_address_collection = ET.SubElement(shipment, "OrganizationAddressCollection")
        org_address = ET.SubElement(org_address_collection, "OrganizationAddress")
        ET.SubElement(org_address, "AddressType").text = "ConsignorDocumentaryAddress"
        ET.SubElement(org_address, "OrganizationCode").text = consignor_code

        # Commercial Invoice with Reconciled CIF Line Items
        ci_collection = ET.SubElement(shipment, "CommercialInvoiceCollection")
        ci = ET.SubElement(ci_collection, "CommercialInvoice")
        ET.SubElement(ci, "InvoiceNumber").text = invoice_number
        
        incoterm_el = ET.SubElement(ci, "Incoterm")
        ET.SubElement(incoterm_el, "Code").text = incoterm

        ET.SubElement(ci, "InvoiceAmount", Currency="USD").text = f"{invoice_amount:.2f}"
        ET.SubElement(ci, "InsuranceAmount", Currency="USD").text = f"{insurance_amount:.2f}"

        lines_collection = ET.SubElement(ci, "CommercialInvoiceLineCollection")
        for item in line_items:
            line_el = ET.SubElement(lines_collection, "CommercialInvoiceLine")
            ET.SubElement(line_el, "LineNumber").text = str(item.get("line_number", 1))
            ET.SubElement(line_el, "Description").text = str(item.get("description", ""))
            ET.SubElement(line_el, "HarmonizedCode").text = str(item.get("hts_code", "8542.31"))
            val = Decimal(str(item.get("value", "0.00")))
            ET.SubElement(line_el, "CustomsValue", Currency="USD").text = f"{val:.2f}"

        # Customized Audit Telemetry
        custom_fields = ET.SubElement(shipment, "CustomizedFieldCollection")
        
        cf_audit = ET.SubElement(custom_fields, "CustomizedField")
        ET.SubElement(cf_audit, "Key").text = "PreAuditVerificationStatus"
        ET.SubElement(cf_audit, "DataType").text = "String"
        ET.SubElement(cf_audit, "Value").text = audit_status

        cf_penalty = ET.SubElement(custom_fields, "CustomizedField")
        ET.SubElement(cf_penalty, "Key").text = "PenaltyExposureMitigated"
        ET.SubElement(cf_penalty, "DataType").text = "String"
        ET.SubElement(cf_penalty, "Value").text = penalty_status

        # Format pretty XML
        xml_bytes = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(xml_bytes)
        return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    def generate_diff_payload(self, audit: "AuditResult") -> Dict[str, Any]:
        """
        Side-by-side UniversalShipment XML for one audit: the document as extracted
        ("raw") versus the document with the audit's corrections applied ("reconciled").
        Every amount comes from ``audit.extracted_data`` and its findings.
        """
        data = audit.extracted_data or {}
        cid = audit.concept_id
        released = audit.quarantine_status == "RELEASED"
        status = "READY_FOR_INGESTION" if released else "HELD_PENDING_REVIEW"
        base = {
            "concept_id": cid,
            "audit_run_id": audit.audit_run_id,
            "schema_version": "1.1",
            "schema_validation": "structural subset (in-repo XSD); not validated against WiseTech-published schemas",
        }
        dest_code = "USLAX" if "LOS ANGELES" in str(data.get("port_of_entry", "LOS ANGELES")).upper() else "UNKNOWN"

        if cid in ("concept_1_customs", "concept_clean_fob"):
            items = [it for it in data.get("items") or [] if isinstance(it, dict)]
            lawful_hts = str(data.get("lawful_hts") or "")
            declared_hts = str(data.get("declared_hts") or "")
            raw_lines, rec_lines, diffs = [], [], []
            for it in items:
                stated = Decimal(str(it.get("stated_total") or "0"))
                calc = (Decimal(str(it.get("quantity") or "0")) * Decimal(str(it.get("unit_price") or "0"))).quantize(Decimal("0.01"))
                hts = str(it.get("hts_code") or "")
                rec_hts = lawful_hts if (declared_hts and hts == declared_hts and lawful_hts) else hts
                raw_lines.append({"line_number": it.get("line_number"), "description": it.get("description", ""), "hts_code": hts, "value": stated})
                rec_lines.append({"line_number": it.get("line_number"), "description": it.get("description", ""), "hts_code": rec_hts, "value": calc})
                if calc != stated:
                    diffs.append({"node": f"CommercialInvoiceLine[{it.get('line_number')}]/CustomsValue", "raw": f"{stated:.2f}",
                                  "reconciled": f"{calc:.2f}", "statute": "19 CFR 141.86", "status": "CORRECTED"})
                if rec_hts != hts:
                    diffs.append({"node": f"CommercialInvoiceLine[{it.get('line_number')}]/HarmonizedCode", "raw": hts,
                                  "reconciled": rec_hts, "statute": "GRI 1 / Note 12(b) to Chapter 85", "status": "RECLASSIFICATION_PROPOSED"})
            freight = Decimal(str(data.get("freight_charge") or "0"))
            insurance = Decimal(str(data.get("insurance_charge") or "0"))
            incoterm = str(data.get("incoterms") or "").split(" ")[0] or "UNK"
            raw_total = sum((ln["value"] for ln in raw_lines), Decimal("0")) + (freight + insurance if incoterm == "CIF" else Decimal("0"))
            rec_total = sum((ln["value"] for ln in rec_lines), Decimal("0"))
            if raw_total != rec_total:
                diffs.append({"node": "InvoiceAmount", "raw": f"{raw_total:.2f}", "reconciled": f"{rec_total:.2f}",
                              "statute": "19 U.S.C. 1401a(b)(4)(A)", "status": "NON_DUTIABLE_CHARGES_DEDUCTED"})
            common: Dict[str, Any] = dict(
                shipment_id=f"S-{audit.audit_run_id[4:14]}",
                declaration_id=f"B-{audit.audit_run_id[4:14]}",
                port_origin_code="CNYTN", port_origin_name="Yantian",
                port_dest_code=dest_code, port_dest_name="Los Angeles / Long Beach",
                invoice_number=str(data.get("invoice_number") or "UNKNOWN"),
                incoterm=incoterm,
                insurance_amount=insurance,
            )
            raw_xml = self.generate_universal_interchange_xml(
                **common, invoice_amount=raw_total, line_items=raw_lines,
                audit_status="UNVERIFIED_RAW_INGEST", penalty_status="UNAUDITED",
            )
            rec_xml = self.generate_universal_interchange_xml(
                **common, invoice_amount=rec_total, line_items=rec_lines,
                audit_status="RECONCILED" if diffs else "CLEARED_NO_EXCEPTIONS",
                penalty_status="EXPOSURE_FLAGGED_FOR_REVIEW" if diffs else "NO_EXCEPTIONS",
            )
            return {**base, "status": status, "raw_unaudited_xml": raw_xml, "reconciled_lawful_xml": rec_xml, "diff_summary": diffs}

        if cid == "concept_2_freight":
            base_freight = Decimal(str(data.get("base_freight") or "0"))
            fsc = (base_freight * Decimal(str(data.get("billed_fsc_rate") or "0"))).quantize(Decimal("0.01"))
            chs = Decimal(str(data.get("chassis_split_fee") or "0"))
            det = Decimal(str(data.get("detention_billed") or "0"))
            raw_total = base_freight + fsc + chs + det
            rec_total = raw_total - audit.metrics.carrier_overbilling_caught
            common = dict(
                shipment_id=f"S-{audit.audit_run_id[4:14]}", declaration_id=f"B-{audit.audit_run_id[4:14]}",
                port_origin_code="CNYTN", port_origin_name="Yantian", port_dest_code="USLAX", port_dest_name="Los Angeles",
                invoice_number=str(data.get("invoice_number") or "UNKNOWN"), incoterm="FOB", insurance_amount=Decimal("0.00"),
                line_items=[{"line_number": 1, "description": "Ocean freight and audited surcharges", "hts_code": "", "value": base_freight}],
            )
            raw_xml = self.generate_universal_interchange_xml(**common, invoice_amount=raw_total,
                                                               audit_status="UNVERIFIED_RAW_INGEST", penalty_status="UNAUDITED")
            rec_xml = self.generate_universal_interchange_xml(**common, invoice_amount=rec_total,
                                                               audit_status="RECONCILED", penalty_status="OVERBILLING_DISPUTED")
            diffs = [] if raw_total == rec_total else [{
                "node": "InvoiceAmount", "raw": f"{raw_total:.2f}", "reconciled": f"{rec_total:.2f}",
                "statute": "Service contract / 46 CFR Part 541", "status": "OVERBILLING_DISPUTED",
            }]
            return {**base, "status": status, "raw_unaudited_xml": raw_xml, "reconciled_lawful_xml": rec_xml, "diff_summary": diffs}

        reason = "BLOCKED_DO_NOT_TRANSMIT" if cid == "concept_4_sanctions" and not released else "NOT_APPLICABLE"
        return {**base, "status": reason, "raw_unaudited_xml": "", "reconciled_lawful_xml": "", "diff_summary": []}


cargowise_exporter = CargoWiseExportService()
cargowise_xml_generator = cargowise_exporter

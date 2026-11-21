import os
import xml.etree.ElementTree as ET
from decimal import Decimal

from lxml import etree

from app.services.cargowise_xml import cargowise_exporter


def test_cargowise_universal_interchange_xsd_validation():
    """Verify generated XML validates strictly against UniversalInterchange v1.1 XSD schema."""
    xsd_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "app", "schemas", "cargowise_universal_structural_subset.xsd"
    )
    assert os.path.exists(xsd_path), f"XSD schema file not found at {xsd_path}"

    with open(xsd_path, "rb") as f:
        schema_root = etree.XML(f.read())
    schema = etree.XMLSchema(schema_root)

    xml_output = cargowise_exporter.generate_universal_interchange_xml(
        shipment_id="S00001000",
        declaration_id="B00001000",
        port_origin_code="CNSZX",
        port_origin_name="Shenzhen",
        port_dest_code="USLAX",
        port_dest_name="Los Angeles",
        invoice_amount=Decimal("148500.00"),
        insurance_amount=Decimal("1450.00"),
    )

    doc = etree.fromstring(xml_output.encode("utf-8"))
    assert schema.validate(doc), f"XML failed XSD validation: {schema.error_log}"


def test_cargowise_configurable_company_and_server_ids():
    """Verify Company/Code, EnterpriseID, and ServerID are configurable via arguments."""
    xml_output = cargowise_exporter.generate_universal_interchange_xml(
        company_code="CUSTOM_CO",
        enterprise_id="ENT99",
        server_id="SRV02",
    )
    assert "<Code>CUSTOM_CO</Code>" in xml_output
    assert "<EnterpriseID>ENT99</EnterpriseID>" in xml_output
    assert "<ServerID>SRV02</ServerID>" in xml_output


def test_cargowise_concept_driven_diff_payload():
    """The diff is built from the audit result, not from literal amounts."""
    from app.services.extractor import extractor_service

    clean = extractor_service.run_audit("concept_clean_fob")
    clean_diff = cargowise_exporter.generate_diff_payload(clean)
    assert clean_diff["diff_summary"] == []
    assert clean_diff["status"] == "READY_FOR_INGESTION"
    assert "CLEARED_NO_EXCEPTIONS" in clean_diff["reconciled_lawful_xml"]
    assert "SSAC-2024-CLN-1048" in clean_diff["reconciled_lawful_xml"]

    customs = extractor_service.run_audit("concept_1_customs")
    customs_diff = cargowise_exporter.generate_diff_payload(customs)
    assert customs_diff["status"] == "HELD_PENDING_REVIEW"
    by_node = {d["node"]: d for d in customs_diff["diff_summary"]}
    # Line 1 extension corrected 25,500 -> 22,500; line 2 reclassified; CIF freight deducted
    assert by_node["CommercialInvoiceLine[1]/CustomsValue"]["reconciled"] == "22500.00"
    assert by_node["CommercialInvoiceLine[2]/HarmonizedCode"]["reconciled"] == "8542.31.0000"
    assert by_node["InvoiceAmount"]["raw"] == "170000.00"
    assert by_node["InvoiceAmount"]["reconciled"] == "162500.00"

    sanctions = extractor_service.run_audit("concept_4_sanctions")
    assert cargowise_exporter.generate_diff_payload(sanctions)["status"] == "BLOCKED_DO_NOT_TRANSMIT"


def test_cargowise_universal_interchange_schema():
    xml_output = cargowise_exporter.generate_universal_interchange_xml(
        shipment_id="S00001000",
        declaration_id="B00001000",
        port_origin_code="ZADUR",
        port_origin_name="Durban",
        port_dest_code="NLRTM",
        port_dest_name="Rotterdam",
        invoice_amount=Decimal("148500.00"),
        insurance_amount=Decimal("1450.00")
    )
    
    assert "<?xml" in xml_output
    assert "UniversalInterchange" in xml_output
    assert "UniversalShipment" in xml_output
    assert "http://www.cargowise.com/Schemas/Universal/2011/11" in xml_output

    # Parse and assert structure
    root = ET.fromstring(xml_output.encode("utf-8"))
    assert "UniversalInterchange" in root.tag

    # Check DataTarget routing
    xml_str = xml_output
    assert "<Type>ForwardingShipment</Type>" in xml_str
    assert "<Key>S00001000</Key>" in xml_str
    assert "<Type>CustomsDeclaration</Type>" in xml_str
    assert "<Key>B00001000</Key>" in xml_str
    assert "<InvoiceAmount Currency=\"USD\">148500.00</InvoiceAmount>" in xml_str
    assert "<InsuranceAmount Currency=\"USD\">1450.00</InsuranceAmount>" in xml_str
    assert "<HarmonizedCode>8542.31</HarmonizedCode>" in xml_str
    assert "<Value>CLEARED_WITH_RECONCILIATION</Value>" in xml_str
    # H2: Durban -> Rotterdam is EU corridor; 19 U.S.C. § 1592 must NOT apply
    assert "<Value>19_USC_1592_PROTECTED</Value>" not in xml_str
    assert "<Value>EU_UCC_COMPLIANT</Value>" in xml_str

    # Verify US destination corridor applies 19 U.S.C. § 1592
    us_xml = cargowise_exporter.generate_universal_interchange_xml(
        port_origin_code="CNSZX",
        port_origin_name="Shenzhen",
        port_dest_code="USLAX",
        port_dest_name="Los Angeles",
        invoice_amount=Decimal("148500.00"),
        insurance_amount=Decimal("1450.00")
    )
    assert "<Value>19_USC_1592_PROTECTED</Value>" in us_xml

def test_cargowise_decimal_precision_no_float_drift():
    # Pass values requiring exact decimal rounding
    xml_output = cargowise_exporter.generate_universal_interchange_xml(
        invoice_amount=Decimal("123456.78"),
        insurance_amount=Decimal("987.65"),
        line_items=[
            {
                "line_number": 1,
                "description": "Precision Sensor Unit",
                "hts_code": "9031.80",
                "value": Decimal("124444.43")
            }
        ]
    )
    assert "123456.78" in xml_output
    assert "987.65" in xml_output
    assert "124444.43" in xml_output
    # Assert zero scientific notation (e.g. 1.2e+05)
    assert "e+" not in xml_output
    assert "E+" not in xml_output

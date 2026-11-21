import os
import tempfile

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.services.freight_audit import audit_freight_bill
from app.services.pdf_field_parser import parse_document


def test_parse_nightmare_01_customs():
    pdf_path = os.path.join(settings.NIGHTMARES_DIR, "nightmare_01_customs_ci.pdf")
    assert os.path.exists(pdf_path), "nightmare_01_customs_ci.pdf must exist"

    parsed = parse_document(pdf_path)
    assert parsed.document_type == "customs_invoice"
    payload = parsed.payload

    assert "CIF" in payload["incoterms"]
    assert payload["freight_charge"] == "4500.00"
    assert payload["insurance_charge"] == "0.00"
    assert len(payload["items"]) >= 3

    item1 = payload["items"][0]
    assert item1["line_number"] == 1
    assert item1["hts_code"] == "8542.31.0000"
    assert item1["quantity"] == "500"
    assert item1["unit_price"] == "45.00"
    assert item1["total_price"] == "25500.00"

    item2 = payload["items"][1]
    assert item2["line_number"] == 2
    assert item2["hts_code"] == "8471.30.0100"
    assert item2["quantity"] == "1000"
    assert item2["unit_price"] == "125.00"
    assert item2["total_price"] == "125000.00"

    assert payload["misclassified_value"] == "125000.00"
    # Rates come from the dated tables for a China-origin invoice dated 12 Apr 2024:
    # 8471.30 Free with no Section 301 measure; 8542.31 Free + 25% Section 301.
    assert payload["invoice_date"] == "2024-04-12"
    assert payload["country_of_origin"] == "CN"
    assert payload["declared_duty_rate"] == "0.00"
    assert payload["lawful_duty_rate"] == "0.25"
    assert parsed.missing_fields == []

    assert len(parsed.bounding_boxes) > 0
    assert "incoterms" in parsed.bounding_boxes
    bb = parsed.bounding_boxes["incoterms"]
    assert 0.0 <= bb.x < 1000.0
    assert 0.0 <= bb.y < 1000.0


def test_parse_clean_01_fob():
    pdf_path = os.path.join(settings.NIGHTMARES_DIR, "clean_01_customs_fob.pdf")
    assert os.path.exists(pdf_path), "clean_01_customs_fob.pdf must exist"

    parsed = parse_document(pdf_path)
    assert parsed.document_type == "customs_invoice"
    payload = parsed.payload

    assert "FOB" in payload["incoterms"]
    # An FOB invoice states no freight or insurance: those fields are absent, not "0.00"
    assert payload["insurance_charge"] is None
    assert payload["freight_charge"] is None
    assert payload["unreported_assists"] == "0.00"  # assists are stated as disclosed
    assert payload["misclassified_value"] is None


def test_parse_nightmare_02_freight():
    pdf_path = os.path.join(settings.NIGHTMARES_DIR, "nightmare_02_freight_audit.pdf")
    assert os.path.exists(pdf_path), "nightmare_02_freight_audit.pdf must exist"

    parsed = parse_document(pdf_path)
    assert parsed.document_type == "freight_invoice"
    payload = parsed.payload

    assert payload["base_freight"] == "4500.00"
    assert payload["billed_fsc_rate"] == "0.325"
    assert payload["authorized_fsc_rate"] == "0.24"
    assert payload["chassis_split_fee"] == "285.00"
    assert payload["detention_billed"] == "880.00"
    assert payload["port_free_days_allowed"] == 5
    assert payload["free_time_basis"] == "calendar"
    assert payload["discharge_date"] == "2024-03-24"
    assert payload["outgate_date"] == "2024-03-28"
    assert payload["invoice_date"] == "2024-04-02"
    assert payload["dnd_missing_fields"] == []

    assert "base_freight" in parsed.bounding_boxes
    assert "chassis_split" in parsed.bounding_boxes
    assert "detention" in parsed.bounding_boxes


def test_parse_nightmare_03_drawback():
    pdf_path = os.path.join(settings.NIGHTMARES_DIR, "nightmare_03_duty_drawback.pdf")
    assert os.path.exists(pdf_path), "nightmare_03_duty_drawback.pdf must exist"

    parsed = parse_document(pdf_path)
    assert parsed.document_type == "drawback_claim"
    payload = parsed.payload

    assert payload["import_entry"] == "CBP-7501-84920184"
    assert payload["export_bl"] == "BGFU-0941824"
    assert payload["duties_paid"] == "27600.00"
    assert payload["entry_date"] == "2024-01-15"
    assert payload["export_date"] == "2024-03-10"
    assert payload["imported_quantity"] == "1000"
    assert payload["exported_quantity"] == "1000"
    assert payload["direct_identification"] is True
    assert "is_timely_5yr_window" not in payload  # computed by the engine, not asserted by the parser


def test_parse_nightmare_04_sanctions():
    pdf_path = os.path.join(settings.NIGHTMARES_DIR, "nightmare_04_ofac_registry.pdf")
    assert os.path.exists(pdf_path), "nightmare_04_ofac_registry.pdf must exist"

    parsed = parse_document(pdf_path)
    assert parsed.document_type == "sanctions_dossier"
    payload = parsed.payload

    assert payload["entity_id"] == "bis-el-cn-0941"
    assert "Global Micro Electronics" in payload["name"]


def test_mutated_pdf_produces_mutated_payload_and_audit():
    """
    Critical verification for C1:
    A newly generated PDF with mutated values (e.g. chassis fee $350.00 and detention $1,500.00)
    MUST extract the mutated values directly from the PDF and compute the correspondingly
    different audit exposure!
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        temp_path = tf.name

    try:
        c = canvas.Canvas(temp_path, pagesize=letter)
        c.drawString(46, 748, "COMMERCIAL FREIGHT INVOICE : INTERMODAL FREIGHT & SURCHARGES DIVISION")
        c.drawString(46, 708, "INVOICE NUMBER: PACL-FRT-MUTATED-999")
        c.drawString(340, 652, "Vessel Discharge Date: March 24, 2024 : Free Time: 7 Days")

        # Table rows
        c.drawString(42, 586, "BAS")
        c.drawString(90, 586, "Base Ocean Freight")
        c.drawString(320, 586, "$5,000.00")
        c.drawString(420, 586, "$5,000.00")

        c.drawString(42, 550, "BAF/FSC")
        c.drawString(90, 550, "Bunker / Fuel Surcharge (Index 30.0% vs 20.0%)")
        c.drawString(320, 550, "$1,000.00")
        c.drawString(420, 550, "$1,500.00")

        c.drawString(42, 520, "CHS")
        c.drawString(90, 520, "Chassis Split Surcharge")
        c.drawString(320, 520, "$0.00")
        c.drawString(420, 520, "$350.00")

        c.drawString(42, 490, "DET/DEM")
        c.drawString(90, 490, "Container Detention (Billed Day 5 inside 7-day free time)")
        c.drawString(320, 490, "$0.00")
        c.drawString(420, 490, "$1,500.00")
        c.drawString(46, 460, "Pier gate log: container out-gated on March 30, 2024 at 10:00.")

        c.save()

        parsed = parse_document(temp_path)
        assert parsed.document_type == "freight_invoice"
        payload = parsed.payload

        assert payload["base_freight"] == "5000.00"
        assert payload["billed_fsc_rate"] == "0.3"
        assert payload["authorized_fsc_rate"] == "0.2"
        assert payload["chassis_split_fee"] == "350.00"
        assert payload["detention_billed"] == "1500.00"
        assert payload["port_free_days_allowed"] == 7
        assert payload["outgate_date"] == "2024-03-30"  # 24-30 March = 7 calendar days
        # The mutated invoice omits B/L, container, invoice date and dispute contact (46 CFR 541.5)
        assert "invoice date" in payload["dnd_missing_fields"]

        # Execute freight audit on the extracted payload
        metrics, discrepancies = audit_freight_bill(payload)
        # Expected overbilling:
        # FSC overbilling: 5000 * (0.3 - 0.2) = 500.00
        # Chassis overbilling: 350.00
        # Detention overbilling: 1500.00 (day 5 held is within 7 days allowed)
        # Total overbilling = 500.00 + 350.00 + 1500.00 = 2350.00
        from decimal import Decimal
        assert metrics.carrier_overbilling_caught == Decimal("2350.00")
        assert {d.id for d in discrepancies} == {"disc-c2-01", "disc-c2-02", "disc-c2-03", "disc-c2-05-missing-info"}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

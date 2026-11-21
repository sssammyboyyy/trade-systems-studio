import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def get_nightmares_dirs() -> list[str]:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(os.path.dirname(current_dir), "data", "nightmares")
    trade_root = os.path.abspath(os.path.join(current_dir, "../../.."))
    frontend_dir = os.path.join(trade_root, "frontend-dashboard", "public", "nightmares")
    os.makedirs(backend_dir, exist_ok=True)
    os.makedirs(frontend_dir, exist_ok=True)
    return [backend_dir, frontend_dir]


def generate_nightmare_01(output_path: str):
    """
    nightmare_01_customs_ci.pdf (2 Pages):
    Page 1: Commercial Invoice & Customs Entry Declaration.
    Page 2: Commercial Packing List & Container Load Plan (SSAC-2024-89912 / PKL-89912).
    Modeled after CBP CROSS Rulings (HQ H301619 / NY N301248).
    Contains:
    1. CIF Incoterms with missing marine cargo insurance (19 CFR Section 152.103)
    2. Arithmetic multiplication error (500 units @ $45.00 listed as $25,500.00)
    3. HTS Misclassification (8471.30.0100 at 0% vs 8542.31.0000 at 25% Section 301)
    """
    c = canvas.Canvas(output_path, pagesize=letter, invariant=1)
    _width, _height = letter  # 612 x 792

    # --- PAGE 1: COMMERCIAL INVOICE ---
    # Top Institutional Header
    c.setStrokeColor(colors.HexColor("#0F172A"))
    c.setFillColor(colors.HexColor("#0F172A"))
    c.rect(36, 730, 540, 36, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(46, 748, "SHENZHEN SHENZHOU ADVANCED SEMICONDUCTORS CO., LTD.")
    c.setFont("Helvetica", 8)
    c.drawString(46, 736, "COMMERCIAL INVOICE & CBP CUSTOMS ENTRY DECLARATION : EXPORT DIVISION")

    # Document Reference & Parties Grid
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(36, 638, 540, 84, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 708, "INVOICE NUMBER:")
    c.drawString(46, 692, "INVOICE DATE:")
    c.drawString(46, 676, "INCOTERMS 2020:")
    c.drawString(46, 660, "PORT OF ENTRY:")
    c.drawString(46, 646, "VESSEL / VOYAGE:")

    c.setFont("Helvetica", 8)
    c.drawString(146, 708, "SSAC-2024-89912")
    c.drawString(146, 692, "April 12, 2024")
    c.drawString(146, 676, "CIF LOS ANGELES, CA (U.S.A.)")
    c.drawString(146, 660, "PORT 2704 - LOS ANGELES / LONG BEACH")
    c.drawString(146, 646, "PACIFIC HORIZON TAIPEI / V.042E (B/L: PHLU7829104)")

    c.setFont("Helvetica-Bold", 8)
    c.drawString(320, 708, "SHIPPER / EXPORTER:")
    c.drawString(320, 676, "CONSIGNEE / IMPORTER OF RECORD:")

    c.setFont("Helvetica", 7.5)
    c.drawString(320, 696, "Shenzhen Shenzhou Semiconductors Ltd, Nanshan District, Shenzhen, CN")
    c.drawString(320, 664, "Pacific Crest Electronics Corp, 1420 Harbor Blvd, Long Beach, CA 90802")
    c.drawString(320, 652, "EIN / IRS # 94-2849102 : CBP Customs Broker: Apex Customs Brokerage LLC #14902")

    # Line Item Table Header
    c.setFillColor(colors.HexColor("#1E293B"))
    c.rect(36, 608, 540, 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(42, 614, "LINE")
    c.drawString(70, 614, "HTS NUMBER")
    c.drawString(150, 614, "DESCRIPTION OF MERCHANDISE")
    c.drawString(340, 614, "QTY (PCS)")
    c.drawString(405, 614, "UNIT PRICE")
    c.drawString(475, 614, "TOTAL (USD)")

    # Line Items
    items = [
        ("001", "8542.31.0000", "DSP Sub-System Controllers", "500", "$45.00", "$25,500.00"),
        ("002", "8471.30.0100", "High-Speed AI Core Processors", "1,000", "$125.00", "$125,000.00"),
        ("003", "8542.39.0000", "Bus Interface Transceiver ICs", "1,000", "$15.00", "$15,000.00")
    ]

    y = 586
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#0F172A"))
    for line, hts, desc, qty, price, total in items:
        c.drawString(44, y, line)
        c.drawString(70, y, hts)
        c.drawString(150, y, desc)
        c.drawString(350, y, qty)
        c.drawString(410, y, price)
        c.drawRightString(566, y, total)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(36, y - 6, 576, y - 6)
        y -= 24

    # Financial Reconciliation & Freight/Insurance Ledger
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setFillColor(colors.HexColor("#F1F5F9"))
    c.rect(36, 410, 540, 95, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 488, "INVOICE FINANCIAL SUMMARY & INCOTERMS 2020 BREAKDOWN:")
    c.drawString(46, 470, "Merchandise Line Item Subtotal:")
    c.drawString(46, 454, "Ocean Freight (Shanghai -> Long Beach):")
    c.drawString(46, 438, "Marine Cargo Insurance (19 CFR Section 152.103):")
    c.drawString(46, 420, "TOTAL DECLARED CIF INVOICE VALUE:")

    c.setFont("Helvetica", 8)
    c.drawRightString(566, 470, "$165,500.00")
    c.drawRightString(566, 454, "$4,500.00")
    c.drawRightString(566, 438, "$0.00  (OMITTED)")
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(566, 420, "$170,000.00 USD")

    # Statutory Discrepancy Warnings & Legal Audit Footnotes
    c.setFillColor(colors.HexColor("#991B1B"))
    c.rect(36, 320, 540, 75, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 380, "AUDIT WARNING: 19 U.S.C. Section 1592 STATUTORY DEFECTS DETECTED")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.HexColor("#7F1D1D"))
    c.drawString(46, 366, "1. INCOTERM MISMATCH: Invoiced CIF Los Angeles with $0.00 Marine Insurance distorting transaction value.")
    c.drawString(46, 354, "2. ARITHMETIC ANOMALY: Line 001 (500 pcs @ $45.00) calculates to $22,500.00, not invoiced $25,500.00.")
    c.drawString(46, 342, "3. HTS MISCLASSIFICATION: Line 002 misdeclared under 8471.30 ($125,000 at 0% duty) rather than 8542.31 (25% Section 301).")
    c.drawString(46, 330, "Statutory Penalty Exposure under 19 U.S.C. Section 1592: 2.0x lawful duty loss (Negligence) or 4.0x (Gross Negligence: $125,000.00).")

    # CBP Filer Certification & Importer Signature
    c.setStrokeColor(colors.HexColor("#94A3B8"))
    c.setFillColor(colors.white)
    c.rect(36, 215, 540, 95, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 294, "CBP FORM 7501 DECLARATION & BROKER CERTIFICATION:")
    c.setFont("Helvetica", 7.5)
    c.drawString(46, 280, "I declare that the information contained on this Commercial Invoice and Entry Summary is true and correct,")
    c.drawString(46, 268, "and that all foreign assists, packing costs, and commissions under 19 CFR Section 152.103 have been fully reported.")

    c.line(46, 235, 260, 235)
    c.line(300, 235, 550, 235)

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(46, 224, "Authorized Signature of Importer / Agent")
    c.drawString(300, 224, "Licensed Customs Broker #14902 Certification")

    # Page Footer
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(46, 195, "SSAC-2024-89912 : Commercial Invoice (Page 1 of 2) : Port 2704 ACE Entry")

    # --- PAGE 2: COMMERCIAL PACKING LIST & CONTAINER LOAD PLAN ---
    c.showPage()

    # Header Page 2
    c.setStrokeColor(colors.HexColor("#0F172A"))
    c.setFillColor(colors.HexColor("#0F172A"))
    c.rect(36, 730, 540, 36, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(46, 748, "SHENZHEN SHENZHOU ADVANCED SEMICONDUCTORS CO., LTD.")
    c.setFont("Helvetica", 8)
    c.drawString(46, 736, "COMMERCIAL PACKING LIST & CONTAINER LOAD SPECIFICATION : REF: PKL-89912")

    # Packing Reference Grid
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(36, 638, 540, 84, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 708, "PACKING LIST REF:")
    c.drawString(46, 692, "RELATED INVOICE:")
    c.drawString(46, 676, "CONTAINER NUMBER:")
    c.drawString(46, 660, "SEAL NUMBER:")
    c.drawString(46, 646, "TOTAL PACKAGES:")

    c.setFont("Helvetica", 8)
    c.drawString(160, 708, "PKL-89912-EXP")
    c.drawString(160, 692, "SSAC-2024-89912")
    c.drawString(160, 676, "PHLU-9182049 (40' HC Container)")
    c.drawString(160, 660, "PHL-SEAL-892104 (High-Security Bolt Seal)")
    c.drawString(160, 646, "34 Palletized Cartons / 1,700 Standard Units")

    c.setFont("Helvetica-Bold", 8)
    c.drawString(340, 708, "TOTAL GROSS WEIGHT:")
    c.drawString(340, 692, "TOTAL NET WEIGHT:")
    c.drawString(340, 676, "TOTAL CUBIC VOLUME:")
    c.drawString(340, 660, "PORT OF DISCHARGE:")
    c.drawString(340, 646, "CUSTOMS VERIFICATION:")

    c.setFont("Helvetica", 8)
    c.drawString(460, 708, "4,820.00 KGS (10,626 LBS)")
    c.drawString(460, 692, "4,150.00 KGS (9,149 LBS)")
    c.drawString(460, 676, "28.40 CBM")
    c.drawString(460, 660, "Los Angeles / Long Beach")
    c.drawString(460, 646, "CBP Hold Status: AUDIT REQUIRED")

    # Packing Table Header
    c.setFillColor(colors.HexColor("#1E293B"))
    c.rect(36, 608, 540, 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(42, 614, "PKGS")
    c.drawString(80, 614, "CASE MARKS & NOS")
    c.drawString(200, 614, "ITEM & DESCRIPTION")
    c.drawString(360, 614, "QTY (PCS)")
    c.drawString(430, 614, "NET WT (KG)")
    c.drawString(505, 614, "GR WT (KG)")

    # Packing Table Rows
    packing_rows = [
        ("CTNS 1-10", "SSAC/LAX/001-010", "ARM Cortex-M4 Microcontroller Core Boards", "500 PCS", "750.00", "870.00"),
        ("CTNS 11-14", "SSAC/LAX/011-014", "High-Performance Neural Tensor Accelerators", "200 PCS", "600.00", "710.00"),
        ("CTNS 15-34", "SSAC/LAX/015-034", "High-Efficiency Switching Power Supplies", "1,000 PCS", "2,800.00", "3,240.00")
    ]

    y2 = 586
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#0F172A"))
    for pkgs, marks, desc, qty, net_w, gr_w in packing_rows:
        c.drawString(42, y2, pkgs)
        c.drawString(80, y2, marks)
        c.drawString(200, y2, desc)
        c.drawString(360, y2, qty)
        c.drawRightString(480, y2, net_w)
        c.drawRightString(566, y2, gr_w)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(36, y2 - 6, 576, y2 - 6)
        y2 -= 24

    # Warehouse Verification & Discrepancy Note
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(36, 420, 540, 100, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 502, "CONTAINER LOAD VERIFICATION & WEIGHT RECONCILIATION:")
    c.setFont("Helvetica", 7.5)
    c.drawString(46, 488, "Verified Gross Mass (VGM) per SOLAS Chapter VI: 4,820.00 kg. Terminal Weighbridge Ticket # LAX-84019.")
    c.drawString(46, 474, "Packaging Type: Heat-treated wooden pallets conforming to ISPM-15 standard stamp CN-44018.")
    c.drawString(46, 460, "Storage & Handling Instructions: Sensitive Microelectronics. Temperature controlled 15C - 25C. Do not stack.")
    c.drawString(46, 444, "Statutory Discrepancy Notice: While physical piece count (1,700 pcs) matches commercial packing list,")
    c.drawString(46, 432, "line 001 unit valuation ($45.00 x 500 = $22,500.00) conflicts with commercial invoice extension of $25,500.00.")

    # CBP Warehouse Receiving Sign-Off
    c.setStrokeColor(colors.HexColor("#94A3B8"))
    c.setFillColor(colors.white)
    c.rect(36, 290, 540, 110, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 382, "PORT TERMINAL RECEIVING CERTIFICATION & SECURITY INSPECTION:")
    c.setFont("Helvetica", 7.5)
    c.drawString(46, 368, "Terminal gate tally confirms 34 cartons received in apparent good order. Seal intact upon vessel discharge.")

    c.line(46, 320, 260, 320)
    c.line(300, 320, 550, 320)

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(46, 308, "Terminal Receiving Superintendent")
    c.drawString(300, 308, "CBP Port Officer / Badge #4819")

    # Page 2 Footer
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(46, 265, "PKL-89912 : Packing List & Load Plan (Page 2 of 2) : Port 2704 ACE Verified")

    c.save()


def generate_nightmare_02(output_path: str):
    """
    nightmare_02_freight_audit.pdf (2 Pages):
    Page 1: Ocean Carrier Freight Invoice with Demurrage & Detention.
    Page 2: Ocean Bill of Lading (B/L PACLU-894102914) & Terminal In-Gate / Out-Gate Free Time Audit Log.
    Modeled on OSRA 2022 / 46 CFR Part 541 demurrage and detention disputes.
    """
    c = canvas.Canvas(output_path, pagesize=letter, invariant=1)
    _width, _height = letter

    # --- PAGE 1: FREIGHT INVOICE ---
    # Ocean Line Brand Header
    c.setStrokeColor(colors.HexColor("#0369A1"))
    c.setFillColor(colors.HexColor("#0369A1"))
    c.rect(36, 730, 540, 36, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(46, 748, "PACIFIC ALLIANCE CONTAINER LINES (GLOBAL OCEAN CARRIER)")
    c.setFont("Helvetica", 8)
    c.drawString(46, 736, "COMMERCIAL FREIGHT INVOICE : INTERMODAL FREIGHT & SURCHARGES DIVISION")

    # Document Reference Grid
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(36, 638, 540, 84, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 708, "INVOICE NUMBER:")
    c.drawString(46, 692, "BILL OF LADING (B/L):")
    c.drawString(46, 676, "VESSEL / VOYAGE:")
    c.drawString(46, 660, "PORT OF LOADING:")
    c.drawString(46, 646, "PORT OF DISCHARGE:")

    c.setFont("Helvetica", 8)
    c.drawString(150, 708, "PACL-FRT-982104")
    c.drawString(150, 692, "PACLU-894102914 (FMC #024810)")
    c.drawString(150, 676, "PACIFIC HORIZON / V.102W")
    c.drawString(150, 660, "YANTIAN (CN YTN)")
    c.drawString(150, 646, "LOS ANGELES / LONG BEACH (US LAX)")

    c.setFont("Helvetica-Bold", 8)
    c.drawString(340, 708, "BILL-TO PARTY (IMPORTER):")
    c.drawString(340, 676, "CONTAINER & SEAL:")

    c.setFont("Helvetica", 7.5)
    c.drawString(340, 696, "Pacific Crest Electronics Corp : Long Beach, CA 90802")
    c.drawString(340, 664, "40' High Cube # PACU-9182049 : Seal: US984102")
    c.drawString(340, 652, "Vessel Discharge Date: March 24, 2024 : Free Time: 5 Calendar Days")
    c.drawString(340, 640, "Invoice Date: April 2, 2024 : Disputes: billing-disputes@pacl.example")

    # Line Item Table Header
    c.setFillColor(colors.HexColor("#0F172A"))
    c.rect(36, 608, 540, 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(42, 614, "CODE")
    c.drawString(90, 614, "SURCHARGE / SERVICE DESCRIPTION")
    c.drawString(310, 614, "CONTRACT RATE")
    c.drawString(410, 614, "BILLED AMOUNT")
    c.drawString(495, 614, "VARIANCE")

    # Freight Charges
    charges = [
        ("BAS", "Base Ocean Freight (40' HC Container)", "$4,500.00", "$4,500.00", "$0.00"),
        ("BAF/FSC", "Bunker / Fuel Surcharge (Index 32.5% vs 24.0%)", "$1,080.00", "$1,462.50", "+$382.50 OVER"),
        ("THC", "Terminal Handling Charges (Origin/Destination)", "$450.00", "$450.00", "$0.00"),
        ("CHS", "Chassis Split & Repositioning Surcharge (Unauthorized)", "$0.00", "$285.00", "+$285.00 UNWARRANTED"),
        ("DET/DEM", "Container Detention (Billed inside 5-day free time)", "$0.00", "$880.00", "+$880.00 UNLAWFUL")
    ]

    y = 586
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#0F172A"))
    for code, desc, base, billed, diff in charges:
        c.drawString(42, y, code)
        c.drawString(90, y, desc)
        c.drawString(320, y, base)
        c.drawString(420, y, billed)

        if "OVER" in diff or "UNWARRANTED" in diff or "UNLAWFUL" in diff:
            c.setFillColor(colors.HexColor("#DC2626"))
            c.setFont("Helvetica-Bold", 8)
        else:
            c.setFillColor(colors.HexColor("#0F172A"))
            c.setFont("Helvetica", 8)

        c.drawRightString(566, y, diff)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica", 8)

        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(36, y - 6, 576, y - 6)
        y -= 24

    # Financial Total Box
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(36, 420, 540, 85, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 488, "FREIGHT INVOICE TOTAL & OVERBILLING RECONCILIATION:")
    c.drawString(46, 470, "Lawful Contractual Freight Total:")
    c.drawString(46, 454, "Unauthorized / Inflated Surcharges (Service Contract SC-2024-PAC-0012):")
    c.drawString(46, 436, "TOTAL CARRIER INVOICED AMOUNT (PAYABLE):")

    c.setFont("Helvetica", 8)
    c.drawRightString(566, 470, "$6,030.00")
    c.setFillColor(colors.HexColor("#DC2626"))
    c.drawRightString(566, 454, "+$1,547.50 (25.7% OVERBILLING)")
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(566, 436, "$7,577.50 USD")

    # FMC Dispute & OSRA Notice
    c.setFillColor(colors.HexColor("#991B1B"))
    c.rect(36, 335, 540, 75, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 395, "FEDERAL MARITIME COMMISSION (FMC) COMPLIANCE DISPUTE NOTICE")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.HexColor("#7F1D1D"))
    c.drawString(46, 381, "1. CHASSIS SPLIT: Accessorial billed with no shipper work order or service-contract rule referenced.")
    c.drawString(46, 369, "2. INFLATED FSC: Billed fuel surcharge index (32.5%) exceeds the published weekly DOE/EIA benchmark (24.0%).")
    c.drawString(46, 357, "3. DETENTION: Billed although gate records show out-gate on day 5 of 5 calendar days of free time.")
    c.drawString(46, 345, "STATUTORY ACTION: Withholding $1,547.50 in unauthorized billing pending carrier charge dispute filing.")

    # Page 1 Footer
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(46, 310, "PACL-FRT-982104 : Freight Audit Invoice (Page 1 of 2) : 46 CFR Part 541 Billing Record")

    # --- PAGE 2: OCEAN BILL OF LADING & TERMINAL FREE-TIME GATE AUDIT ---
    c.showPage()

    # Header Page 2
    c.setStrokeColor(colors.HexColor("#0369A1"))
    c.setFillColor(colors.HexColor("#0369A1"))
    c.rect(36, 730, 540, 36, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(46, 748, "PACIFIC ALLIANCE CONTAINER LINES (OCEAN BILL OF LADING)")
    c.setFont("Helvetica", 8)
    c.drawString(46, 736, "NON-NEGOTIABLE OCEAN BILL OF LADING & PIER TERMINAL FREE TIME RECORD : B/L: PACLU-894102914")

    # Bill of Lading Spec Grid
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(36, 620, 540, 100, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 706, "B/L NUMBER:")
    c.drawString(46, 690, "SHIPPER / FORWARDER:")
    c.drawString(46, 674, "CONSIGNEE:")
    c.drawString(46, 658, "NOTIFY PARTY:")
    c.drawString(46, 642, "PLACE OF RECEIPT:")
    c.drawString(46, 628, "OCEAN VESSEL:")

    c.setFont("Helvetica", 8)
    c.drawString(160, 706, "PACLU-894102914 (Service Contract: SC-2024-PAC-0012)")
    c.drawString(160, 690, "Shenzhen Shenzhou Semiconductors Ltd / Apex Forwarding")
    c.drawString(160, 674, "Pacific Crest Electronics Corp, Long Beach, CA 90802")
    c.drawString(160, 658, "Apex Customs Brokerage LLC (Broker #14902)")
    c.drawString(160, 642, "Yantian Port CFS, Shenzhen, China")
    c.drawString(160, 628, "PACIFIC HORIZON / VOYAGE 102W : Flag: Panama")

    # Free Time Gate Audit Ledger
    c.setFillColor(colors.HexColor("#1E293B"))
    c.rect(36, 580, 540, 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(42, 586, "EVENT")
    c.drawString(110, 586, "TERMINAL LOCATION")
    c.drawString(240, 586, "DATE & TIMESTAMP")
    c.drawString(380, 586, "FREE-TIME STATUS")
    c.drawString(490, 586, "BILLABILITY")

    gate_events = [
        ("Vessel Arrival", "Pier 400 Berth 402, LAX", "March 23, 2024 14:20 PST", "Pre-Discharge", "Non-Billable"),
        ("Discharged", "Pier 400 Stacking Block B", "March 24, 2024 08:30 PST", "Day 1 of 5 (Free Time Starts)", "Free Time Active"),
        ("Customs Release", "CBP 1C Entry Clear", "March 25, 2024 11:15 PST", "Day 2 of 5 (Free Time)", "Free Time Active"),
        ("Carrier In-Gate", "Chassis Swap Yard Block 4", "March 27, 2024 09:40 PST", "Day 4 of 5 (Inside Free Time)", "Billed $880 UNLAWFUL"),
        ("Out-Gate Tally", "Pier 400 Gate 12 Trucking", "March 28, 2024 13:10 PST", "Day 5 of 5 (Final Free Day)", "Delivered On Time")
    ]

    y3 = 556
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#0F172A"))
    for ev, loc, ts, stat, bill in gate_events:
        c.drawString(42, y3, ev)
        c.drawString(110, y3, loc)
        c.drawString(240, y3, ts)
        c.drawString(380, y3, stat)
        if "UNLAWFUL" in bill:
            c.setFillColor(colors.HexColor("#DC2626"))
            c.setFont("Helvetica-Bold", 8)
        else:
            c.setFillColor(colors.HexColor("#0F172A"))
            c.setFont("Helvetica", 8)
        c.drawString(490, y3, bill)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica", 8)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(36, y3 - 6, 576, y3 - 6)
        y3 -= 24

    # Terminal Free-Time Legal Invariant
    c.setStrokeColor(colors.HexColor("#0369A1"))
    c.setFillColor(colors.HexColor("#F0F9FF"))
    c.rect(36, 370, 540, 80, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0369A1"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 436, "FREE-TIME EVIDENCE (46 CFR 545.5 / 46 CFR PART 541):")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.HexColor("#0C4A6E"))
    c.drawString(46, 422, "Pier 400 gate log proves container PACU-9182049 out-gated on March 28, 2024 at 13:10 PST.")
    c.drawString(46, 410, "Discharge on March 24, 2024 gives 5 calendar days of free time (March 24-28 inclusive).")
    c.drawString(46, 396, "The $880.00 detention fee was billed although the container out-gated on the last free day.")
    c.drawString(46, 382, "Conclusion: the $880.00 detention charge is not supported by the free-time record.")

    # Page 2 Footer
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(46, 330, "PACLU-894102914 : Ocean B/L & Free-Time Gate Log (Page 2 of 2) : Pier 400 LAX Terminal")

    c.save()


def generate_nightmare_03(output_path: str):
    """
    nightmare_03_duty_drawback.pdf (2 Pages):
    Page 1: Paired CBP Form 7501 Import Summary + 19 U.S.C. Section 1313 Drawback Claim.
    Page 2: Paired Export Bill of Lading (B/L BGFU-0941824) with Direct Identification Proof.
    """
    c = canvas.Canvas(output_path, pagesize=letter, invariant=1)
    _width, _height = letter

    # --- PAGE 1: CBP FORM 7501 IMPORT & CLAIM ---
    c.setStrokeColor(colors.HexColor("#047857"))
    c.setFillColor(colors.HexColor("#047857"))
    c.rect(36, 730, 540, 36, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(46, 748, "U.S. CUSTOMS AND BORDER PROTECTION : ENTRY SUMMARY & DRAWBACK CLAIM")
    c.setFont("Helvetica", 8)
    c.drawString(46, 736, "CBP FORM 7501 IMPORT LIQUIDATION MATCHED TO EXPORT BILL OF LADING : 19 U.S.C. Section 1313")

    # Import Summary Section
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(36, 615, 540, 105, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 705, "CBP ENTRY NUMBER:")
    c.drawString(46, 691, "ENTRY DATE:")
    c.drawString(46, 677, "PORT OF ENTRY:")
    c.drawString(46, 663, "IMPORTER OF RECORD:")
    c.drawString(46, 649, "HTS CLASSIFICATION:")
    c.drawString(46, 631, "DUTIES & FEES TENDERED:")

    c.setFont("Helvetica", 8)
    c.drawString(180, 705, "CBP-7501-84920184")
    c.drawString(180, 691, "January 15, 2024 (Liquidated Entry)")
    c.drawString(180, 677, "Port 2704 - Los Angeles / Long Beach")
    c.drawString(180, 663, "Pacific Crest Electronics Corp (IRS # 94-2849102)")
    c.drawString(180, 649, "8542.31.0001 (Electronic Integrated Circuits - Processors)")
    c.setFont("Helvetica-Bold", 8)
    c.drawString(180, 631, "$27,600.00 Duties Paid (Section 301 at 25% on $110,400 Entered Value, 1,000 Units)")

    # Export Match Section
    c.setStrokeColor(colors.HexColor("#047857"))
    c.setFillColor(colors.HexColor("#ECFDF5"))
    c.rect(36, 385, 540, 215, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#065F46"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 585, "19 U.S.C. Section 1313 UNUSED MERCHANDISE DRAWBACK MATCHING VERIFICATION:")

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 472, "Export Carrier / Vessel:")
    c.drawString(46, 458, "Export Ocean Bill of Lading:")
    c.drawString(46, 444, "Export Departure Date:")
    c.drawString(46, 430, "Port of Export / Destination:")
    c.drawString(46, 416, "Exported Quantity / Part:")
    c.drawString(46, 396, "STATUTORY 99% DUTY DRAWBACK REFUND:")

    c.setFont("Helvetica", 8)
    c.drawString(180, 472, "Beacon Global Forwarding / Fictional Pacific Lines (Vessel: PACIFIC HORIZON)")
    c.drawString(180, 458, "BGFU-0941824 (Export Declaration ITN: X20240310998)")
    c.drawString(180, 444, "March 10, 2024 (Exported 55 Days Post-Import Entry)")
    c.drawString(180, 430, "Port of Los Angeles -> Rotterdam, Netherlands (NLRTM)")
    c.drawString(180, 416, "1,000 Units Embedded Processor Modules (Matched by Serial Range)")

    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(566, 396, "$27,324.00 CASH REFUND")
    c.line(46, 408, 566, 408)

    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(46, 376, "Statutory Formula: Lawful Duties Paid ($27,600.00) x 99% Drawback Allowance = $27,324.00 Net Refund.")
    c.drawString(46, 362, "Export and claim fall within the 5-year limit of 19 U.S.C. Section 1313(r)(1).")
    c.drawString(46, 350, "Prepared for filing as an ACE drawback entry (type 47) by a licensed customs broker.")

    # Customs Broker Signature & Submission Box
    c.setStrokeColor(colors.HexColor("#94A3B8"))
    c.setFillColor(colors.white)
    c.rect(36, 215, 540, 115, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 316, "CBP DRAWBACK DECLARATION & LIQUIDATION CERTIFICATION:")
    c.setFont("Helvetica", 7.5)
    c.drawString(46, 302, "I certify that the merchandise described herein was imported, duty paid, and exported without being subjected")
    c.drawString(46, 290, "to any manufacturing process other than inspection and packaging, fulfilling all criteria under 19 U.S.C. Section 1313.")

    c.line(46, 250, 260, 250)
    c.line(300, 250, 550, 250)

    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(46, 238, "Claimant Authorized Officer: Pacific Crest Electronics")
    c.drawString(300, 238, "Drawback Broker Specialist License: #21904")

    # Page 1 Footer
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(46, 185, "CBP-7501-84920184 : Entry Summary & Drawback Claim (Page 1 of 2) : 19 U.S.C. Section 1313")

    # --- PAGE 2: PAIRED EXPORT OCEAN BILL OF LADING ---
    c.showPage()

    c.setStrokeColor(colors.HexColor("#047857"))
    c.setFillColor(colors.HexColor("#047857"))
    c.rect(36, 730, 540, 36, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(46, 748, "BEACON GLOBAL FORWARDING / FICTIONAL PACIFIC LINES (EXPORT BILL OF LADING)")
    c.setFont("Helvetica", 8)
    c.drawString(46, 736, "OCEAN EXPORT MANIFEST & DIRECT IDENTIFICATION MATCHING PROOF : B/L: BGFU-0941824")

    # Export Spec Grid
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(36, 620, 540, 100, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 706, "EXPORT B/L NO:")
    c.drawString(46, 690, "EXPORTER / FORWARDER:")
    c.drawString(46, 674, "CONSIGNEE (OVERSEAS):")
    c.drawString(46, 658, "AES ITN NUMBER:")
    c.drawString(46, 642, "PORT OF LADING:")
    c.drawString(46, 628, "FINAL DESTINATION:")

    c.setFont("Helvetica", 8)
    c.drawString(180, 706, "BGFU-0941824 (Ocean Export Bill of Lading)")
    c.drawString(180, 690, "Pacific Crest Electronics Corp, Long Beach, CA (IRS 94-2849102)")
    c.drawString(180, 674, "EuroTech Micro Distributie B.V., Rotterdam, Netherlands")
    c.drawString(180, 658, "X20240310998 (Electronic Export Information Automated Filing)")
    c.drawString(180, 642, "Port of Los Angeles (Port Code 2704)")
    c.drawString(180, 628, "Port of Rotterdam (NLRTM) : On Board PACIFIC HORIZON")

    # Line Item Drawback Traceability
    c.setFillColor(colors.HexColor("#065F46"))
    c.rect(36, 580, 540, 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(42, 586, "ITEM")
    c.drawString(80, 586, "SERIAL RANGE")
    c.drawString(220, 586, "IMPORT ENTRY MATCH")
    c.drawString(380, 586, "QTY EXPORTED")
    c.drawString(480, 586, "DUTY REFUND (99%)")

    trace_items = [
        ("001", "SSD-M4-00100 to 00599", "CBP-7501-84920184 (Line 1)", "500 PCS", "$13,662.00"),
        ("002", "SSD-M4-00600 to 01099", "CBP-7501-84920184 (Line 2)", "500 PCS", "$13,662.00")
    ]

    y4 = 556
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#0F172A"))
    for item_n, serials, match_line, qty, refund in trace_items:
        c.drawString(42, y4, item_n)
        c.drawString(80, y4, serials)
        c.drawString(220, y4, match_line)
        c.drawString(380, y4, qty)
        c.drawRightString(566, y4, refund)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(36, y4 - 6, 576, y4 - 6)
        y4 -= 24

    # Statutory Drawback Recapitulation
    c.setStrokeColor(colors.HexColor("#059669"))
    c.setFillColor(colors.HexColor("#ECFDF5"))
    c.rect(36, 440, 540, 90, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#065F46"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 514, "CBP ACE DRAWBACK SUMMARY & LIQUIDATION CERTIFICATE:")
    c.setFont("Helvetica", 7.5)
    c.drawString(46, 498, "Total Lawful General Duties Tendered on Import: $27,600.00 USD.")
    c.drawString(46, 484, "Total Direct Identification Matched Export Quantity: 1,000 / 1,000 Units (100% Correlation).")
    c.drawString(46, 470, "19 U.S.C. Section 1313 Net Duty Drawback Payable: $27,324.00 USD (99.00% Statutory Standard).")
    c.drawString(46, 454, "Status: Certified for Accelerated Payment by Licensed Customs Broker #21904.")

    # Page 2 Footer
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(46, 400, "BGFU-0941824 : Export Ocean B/L & Drawback Match (Page 2 of 2) : 19 U.S.C. Section 1313")

    c.save()


def generate_clean_01(output_path: str):
    """
    clean_01_customs_fob.pdf (2 Pages):
    Page 1: Certified Commercial Invoice (FOB Export Declaration).
    Page 2: Certified Packing List & 19 CFR Section 152.103 GAAP Assist Allocation Ledger.
    """
    c = canvas.Canvas(output_path, pagesize=letter, invariant=1)
    _width, _height = letter

    # --- PAGE 1: COMMERCIAL INVOICE ---
    c.setStrokeColor(colors.HexColor("#0F172A"))
    c.setFillColor(colors.HexColor("#0F172A"))
    c.rect(36, 730, 540, 36, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(46, 748, "SHENZHEN ADVANCED SEMICONDUCTORS CO., LTD.")
    c.setFont("Helvetica", 8)
    c.drawString(46, 736, "CERTIFIED COMMERCIAL INVOICE : FOB EXPORT DECLARATION : COMPLIANT FILING")

    # Document Reference Grid
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(36, 638, 540, 84, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 708, "INVOICE NUMBER:")
    c.drawString(46, 692, "INVOICE DATE:")
    c.drawString(46, 676, "INCOTERMS 2020:")
    c.drawString(46, 660, "PORT OF ENTRY:")
    c.drawString(46, 646, "VESSEL / VOYAGE:")

    c.setFont("Helvetica", 8)
    c.drawString(146, 708, "SSAC-2024-CLN-1048")
    c.drawString(146, 692, "May 18, 2024")
    c.drawString(146, 676, "FOB YANTIAN, CHINA (VERIFIED)")
    c.drawString(146, 660, "PORT 2704 - LOS ANGELES / LONG BEACH")
    c.drawString(146, 646, "PACIFIC HORIZON VOYAGER / V.2405")

    c.setFont("Helvetica-Bold", 8)
    c.drawString(320, 708, "SHIPPER / EXPORTER:")
    c.drawString(320, 676, "CONSIGNEE / IMPORTER OF RECORD:")

    c.setFont("Helvetica", 7.5)
    c.drawString(320, 696, "Shenzhen Advanced Semiconductors Ltd, High-Tech Industrial Park, CN")
    c.drawString(320, 664, "Pacific Crest Electronics Corp, Long Beach, CA 90802")
    c.drawString(320, 652, "EIN / IRS # 94-2849102 : Licensed Broker #14902")

    # Line Item Table Header
    c.setFillColor(colors.HexColor("#1E293B"))
    c.rect(36, 608, 540, 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(42, 614, "LINE")
    c.drawString(70, 614, "HTS NUMBER")
    c.drawString(150, 614, "DESCRIPTION OF MERCHANDISE")
    c.drawString(340, 614, "QTY (PCS)")
    c.drawString(405, 614, "UNIT PRICE")
    c.drawString(475, 614, "TOTAL (USD)")

    # Line Items
    items = [
        ("001", "8542.31.0001", "ARM Cortex-M4 Microcontroller Processors", "500", "$45.00", "$22,500.00"),
        ("002", "8542.31.0001", "High-Performance Neural Tensor Accelerators", "200", "$350.00", "$70,000.00"),
        ("003", "8504.40.9580", "High-Efficiency Switching Power Supplies", "1,000", "$25.00", "$25,000.00")
    ]

    y = 586
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#0F172A"))
    for line, hts, desc, qty, price, total in items:
        c.drawString(44, y, line)
        c.drawString(70, y, hts)
        c.drawString(150, y, desc)
        c.drawString(350, y, qty)
        c.drawString(410, y, price)
        c.drawRightString(566, y, total)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(36, y - 6, 576, y - 6)
        y -= 24

    # Reconciliation Box
    c.setStrokeColor(colors.HexColor("#059669"))
    c.setFillColor(colors.HexColor("#ECFDF5"))
    c.rect(36, 420, 540, 85, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#065F46"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 488, "STATUTORY VALUATION COMPLIANCE CERTIFICATION (19 CFR Section 152.103):")
    c.drawString(46, 470, "FOB Transaction Value (No Non-Dutiable Freight Contamination):")
    c.drawString(46, 454, "Certified GAAP Buyer-Supplied Assists Disclosed (AST-2026-001):")
    c.drawString(46, 436, "TOTAL LAWFUL DUTIABLE VALUE DECLARED:")

    c.setFont("Helvetica", 8)
    c.drawRightString(566, 470, "$117,500.00")
    c.drawRightString(566, 454, "$27,750.00 (Disclosed)")
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(566, 436, "$145,250.00 USD")

    # Green Clean Badge
    c.setFillColor(colors.HexColor("#065F46"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 380, "ZERO STATUTORY DEFECTS DETECTED : BASELINE CLEAN FIXTURE (DEMO)")
    c.setFont("Helvetica", 7.5)
    c.drawString(46, 366, "1. Arithmetic cross-multiplication verified: 100% exact match ($22,500.00 + $70,000.00 + $25,000.00 = $117,500.00).")
    c.drawString(46, 354, "2. FOB terms strictly segregated from ocean freight; zero risk of double taxation on international logistics overhead.")
    c.drawString(46, 342, "3. All tooling assists amortized and declared in compliance with 19 CFR Section 152.103(e). Zero Section 1592 exposure.")

    # Page 1 Footer
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(46, 310, "SSAC-2024-CLN-1048 : Certified Invoice (Page 1 of 2) : Port 2704 Entry")

    # --- PAGE 2: CERTIFIED PACKING LIST & GAAP ASSISTS LEDGER ---
    c.showPage()

    c.setStrokeColor(colors.HexColor("#0F172A"))
    c.setFillColor(colors.HexColor("#0F172A"))
    c.rect(36, 730, 540, 36, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(46, 748, "SHENZHEN ADVANCED SEMICONDUCTORS CO., LTD.")
    c.setFont("Helvetica", 8)
    c.drawString(46, 736, "CERTIFIED PACKING LIST & 19 CFR Section 152.103 GAAP ASSIST LEDGER : PKL-CLN-1048")

    # Spec Grid
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(36, 620, 540, 100, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 706, "PACKING SPEC:")
    c.drawString(46, 690, "INVOICE LINK:")
    c.drawString(46, 674, "CONTAINER / SEAL:")
    c.drawString(46, 658, "ASSIST REGISTRATION:")
    c.drawString(46, 642, "AMORTIZATION METHOD:")
    c.drawString(46, 628, "IMPORTER BROKER:")

    c.setFont("Helvetica", 8)
    c.drawString(180, 706, "34 Heat-Treated Wooden Pallets : ISPM-15 Certified")
    c.drawString(180, 690, "SSAC-2024-CLN-1048 (FOB Yantian Entry)")
    c.drawString(180, 674, "PHLU-8921048 / Seal: PH-982104 (High Security)")
    c.drawString(180, 658, "AST-2026-001 (Microcontroller Production Tooling)")
    c.drawString(180, 642, "Units Produced Method per 19 CFR Section 152.103(e)")
    c.drawString(180, 628, "Apex Customs Brokerage LLC (#14902)")

    # Assist Ledger Table
    c.setFillColor(colors.HexColor("#065F46"))
    c.rect(36, 580, 540, 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(42, 586, "ASSIST REF")
    c.drawString(120, 586, "DESCRIPTION OF ASSIST")
    c.drawString(280, 586, "TOTAL ASSET COST")
    c.drawString(400, 586, "AMORTIZED ENTRY")
    c.drawString(500, 586, "STATUS")

    assist_rows = [
        ("AST-2026-001A", "Photolithography Mask Set 14nm", "$85,000.00", "$15,250.00", "Disclosed"),
        ("AST-2026-001B", "Custom Die Casting Molds (Cortex)", "$50,000.00", "$12,500.00", "Disclosed")
    ]

    y5 = 556
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#0F172A"))
    for aref, adesc, acost, aentry, astatus in assist_rows:
        c.drawString(42, y5, aref)
        c.drawString(120, y5, adesc)
        c.drawString(280, y5, acost)
        c.drawString(400, y5, aentry)
        c.drawString(500, y5, astatus)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(36, y5 - 6, 576, y5 - 6)
        y5 -= 24

    # Compliance Sign-off
    c.setStrokeColor(colors.HexColor("#059669"))
    c.setFillColor(colors.HexColor("#ECFDF5"))
    c.rect(36, 440, 540, 85, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#065F46"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 510, "CBP VALUE DECLARATION AUDIT COMPLETION:")
    c.setFont("Helvetica", 7.5)
    c.drawString(46, 496, "All buyer-supplied tools and foreign development costs have been properly capitalized and declared.")
    c.drawString(46, 482, "19 CFR Section 152.103 transaction value calculation audited and confirmed without deduction errors.")
    c.drawString(46, 468, "Entry summary cleared for automatic green-lane bypass into ACE.")

    # Page 2 Footer
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(46, 400, "PKL-CLN-1048 : Certified Packing List & Assist Ledger (Page 2 of 2) : Port 2704 Entry")

    c.save()


def generate_nightmare_04(output_path: str):
    """
    nightmare_04_ofac_registry.pdf (2 Pages):
    Page 1: OFAC SDN & BIS Denied Persons Regulatory Screening Report & Corporate Lineage.
    Page 2: Multi-Tier Beneficial Ownership Register & 31 CFR Section 501 Aggregate Blocked Equity Ledger.
    Target: Global Micro Electronics Ltd (bis-el-cn-0941).
    Demonstrates: Victor Petrov (25%) + Rosoboronexport JSC (30%) = 55% Cumulative Blocked Ownership.
    """
    c = canvas.Canvas(output_path, pagesize=letter, invariant=1)
    _width, _height = letter

    # --- PAGE 1: SANCTIONS & REGULATORY SCREENING DOSSIER ---
    c.setStrokeColor(colors.HexColor("#991B1B"))
    c.setFillColor(colors.HexColor("#991B1B"))
    c.rect(36, 730, 540, 36, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(46, 748, "TRADE COMPLIANCE ENFORCEMENT : SANCTIONS & DENIED PARTY SCREENING")
    c.setFont("Helvetica", 8)
    c.drawString(46, 736, "OFAC SDN LIST & BIS ENTITY LIST WATCHLIST INTERROGATION : 31 CFR Section 501 / EAR PART 744")

    # Document Reference Grid
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(36, 620, 540, 100, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 706, "TARGET LEGAL ENTITY:")
    c.drawString(46, 690, "ENTITY IDENTIFIER:")
    c.drawString(46, 674, "REGISTRATION ADDRESS:")
    c.drawString(46, 658, "PRIMARY ENFORCEMENT:")
    c.drawString(46, 642, "REGULATORY TOPICS:")
    c.drawString(46, 628, "SCREENING STATUS:")

    c.setFont("Helvetica", 8)
    c.drawString(180, 706, "Global Micro Electronics Ltd (GME Shenzhen) [FICTITIOUS DEMO ENTITY]")
    c.drawString(180, 690, "bis-el-cn-0941 (OpenSanctions FollowTheMoney v3 Schema)")
    c.drawString(180, 674, "Building 4, High-Tech Industrial Zone, Nanshan District, Shenzhen, CN")
    c.drawString(180, 658, "BIS Entity List (15 CFR Part 744, Supp. No. 4) : EAR Military End-User")
    c.drawString(180, 642, "sanction : export.control : military : dual.use")
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.HexColor("#DC2626"))
    c.drawString(180, 628, "BLOCKED ENTITY : MANDATORY TRANSACTION EMBARGO")

    # Regulatory Match Findings
    c.setFillColor(colors.HexColor("#1E293B"))
    c.rect(36, 580, 540, 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(42, 586, "RULE")
    c.drawString(100, 586, "MATCHED PARTY / ALIAS")
    c.drawString(280, 586, "PROGRAM AUTHORITY")
    c.drawString(450, 586, "CONFIDENCE")

    matches = [
        ("EXACT", "Global Micro Electronics Ltd [DEMO]", "BIS Entity List (15 CFR Part 744)", "100.0% MATCH"),
        ("ALIAS", "GME Shenzhen [DEMO]", "EAR Military End-User Restriction", "92.4% MATCH"),
        ("50% RULE", "Victor Petrov (SDN Oligarch Holding) [DEMO]", "OFAC SDN / E.O. 14024", "25.0% EQUITY"),
        ("50% RULE", "Rosoboronexport JSC Holding [DEMO]", "CAATSA Section 231 / EU Reg", "30.0% EQUITY")
    ]

    y6 = 556
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#0F172A"))
    for mrule, mparty, mprog, mconf in matches:
        c.drawString(42, y6, mrule)
        c.drawString(100, y6, mparty)
        c.drawString(280, y6, mprog)
        if "MATCH" in mconf or "EQUITY" in mconf:
            c.setFillColor(colors.HexColor("#DC2626"))
            c.setFont("Helvetica-Bold", 8)
        else:
            c.setFillColor(colors.HexColor("#0F172A"))
            c.setFont("Helvetica", 8)
        c.drawRightString(566, y6, mconf)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica", 8)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(36, y6 - 6, 576, y6 - 6)
        y6 -= 24

    # Statutory Enforcement Warning
    c.setStrokeColor(colors.HexColor("#991B1B"))
    c.setFillColor(colors.HexColor("#FEF2F2"))
    c.rect(36, 410, 540, 95, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#991B1B"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 490, "31 CFR Section 501 / OFAC 50 PERCENT RULE STATUTORY VIOLATION:")
    c.setFont("Helvetica", 7.5)
    c.drawString(46, 474, "Direct and indirect cumulative ownership by blocked persons exceeds 50.0% statutory threshold (55.0% Total).")
    c.drawString(46, 460, "Under OFAC regulations, any entity owned 50 percent or more in the aggregate by one or more blocked persons")
    c.drawString(46, 446, "is itself considered a blocked person, regardless of whether the entity is specifically named on the SDN List.")
    c.drawString(46, 432, "COMPLIANCE MANDATE: Prohibited transaction. Any U.S. Person must block property and file report within 10 days.")

    # Page 1 Footer
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(46, 385, "bis-el-cn-0941 : Sanctions Screening Report (Page 1 of 2) : 31 CFR Section 501 / BIS Watchlist")

    # --- PAGE 2: MULTI-TIER BENEFICIAL OWNERSHIP & 50% RULE LEDGER ---
    c.showPage()

    c.setStrokeColor(colors.HexColor("#991B1B"))
    c.setFillColor(colors.HexColor("#991B1B"))
    c.rect(36, 730, 540, 36, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(46, 748, "OFAC 50% RULE : BENEFICIAL OWNERSHIP & EQUITY AGGREGATION LEDGER")
    c.setFont("Helvetica", 8)
    c.drawString(46, 736, "RECURSIVE GRAPH TRAVERSAL & CORPORATE CONTROL STRUCTURE : TARGET: bis-el-cn-0941")

    # Graph Specification Summary
    c.setStrokeColor(colors.HexColor("#334155"))
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(36, 620, 540, 100, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 706, "TARGET ID:")
    c.drawString(46, 690, "PRIMARY SHAREHOLDERS:")
    c.drawString(46, 674, "BLOCKED ENTITY 1:")
    c.drawString(46, 658, "BLOCKED ENTITY 2:")
    c.drawString(46, 642, "COMMERCIAL MINORITY:")
    c.drawString(46, 628, "AGGREGATE BLOCKED EQUITY:")

    c.setFont("Helvetica", 8)
    c.drawString(180, 706, "bis-el-cn-0941 (Global Micro Electronics Ltd) [FICTITIOUS DEMO ENTITY]")
    c.drawString(180, 690, "3 Beneficial Owners identified via FollowTheMoney corporate ownership edges")
    c.drawString(180, 674, "Victor Petrov [DEMO] (SDN Oligarch : E.O. 14024) : 25.0% Direct Equity")
    c.drawString(180, 658, "Rosoboronexport JSC [DEMO] (CAATSA Section 231) : 30.0% Direct Equity")
    c.drawString(180, 642, "Shenzhen Advanced Components Ltd (Unsanctioned Commercial) : 45.0% Equity")
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.HexColor("#DC2626"))
    c.drawString(180, 628, "55.0% BLOCKED OWNERSHIP (EXCEEDS 50.0% STATUTORY THRESHOLD)")

    # Ownership Ledger Table
    c.setFillColor(colors.HexColor("#1E293B"))
    c.rect(36, 580, 540, 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(42, 586, "NODE ID")
    c.drawString(120, 586, "SHAREHOLDER ENTITY NAME")
    c.drawString(300, 586, "RELATIONSHIP")
    c.drawString(410, 586, "EQUITY %")
    c.drawString(490, 586, "SANCTION STATUS")

    ownership_table = [
        ("node-petrov", "Victor Petrov", "Beneficial Owner", "25.00%", "OFAC SDN BLOCKED"),
        ("node-rosoboron", "Rosoboronexport JSC", "Equity Holding", "30.00%", "OFAC SDN BLOCKED"),
        ("node-shenzhen-adv", "Shenzhen Advanced Components", "Commercial Shareholder", "45.00%", "CLEAN COMMERCIAL")
    ]

    y7 = 556
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#0F172A"))
    for nid, nname, nrel, neq, nstat in ownership_table:
        c.drawString(42, y7, nid)
        c.drawString(120, y7, nname)
        c.drawString(300, y7, nrel)
        c.drawString(410, y7, neq)
        if "BLOCKED" in nstat:
            c.setFillColor(colors.HexColor("#DC2626"))
            c.setFont("Helvetica-Bold", 8)
        else:
            c.setFillColor(colors.HexColor("#059669"))
            c.setFont("Helvetica", 8)
        c.drawString(490, y7, nstat)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica", 8)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(36, y7 - 6, 576, y7 - 6)
        y7 -= 24

    # OFAC Statutory Audit Conclusion
    c.setStrokeColor(colors.HexColor("#991B1B"))
    c.setFillColor(colors.HexColor("#FEF2F2"))
    c.rect(36, 420, 540, 100, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#991B1B"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(46, 502, "LEGAL DETERMINATION UNDER 31 CFR Section 501 / OFAC 50% RULE:")
    c.setFont("Helvetica", 7.5)
    c.drawString(46, 488, "Victor Petrov (25.0%) and Rosoboronexport JSC (30.0%) jointly hold 55.0% of Global Micro Electronics Ltd.")
    c.drawString(46, 474, "Although no individual blocked shareholder holds a standalone 50% majority, aggregate blocked interest")
    c.drawString(46, 460, "meets and surpasses the statutory 50.0% threshold mandated by 31 CFR Section 501.")
    c.drawString(46, 446, "Action Required: Global Micro Electronics Ltd is deemed fully blocked by operation of law. Wire release denied.")
    c.drawString(46, 432, "CargoWise eAdaptor Action: Halt XML transmission to carrier; trigger immediate compliance quarantine.")

    # Page 2 Footer
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawString(46, 385, "bis-el-cn-0941 : OFAC 50% Rule Corporate Control Ledger (Page 2 of 2) : 31 CFR Section 501")

    c.save()


def generate_all_nightmares():
    dirs = get_nightmares_dirs()
    for d in dirs:
        generate_nightmare_01(os.path.join(d, "nightmare_01_customs_ci.pdf"))
        generate_nightmare_02(os.path.join(d, "nightmare_02_freight_audit.pdf"))
        generate_nightmare_03(os.path.join(d, "nightmare_03_duty_drawback.pdf"))
        generate_clean_01(os.path.join(d, "clean_01_customs_fob.pdf"))
        generate_nightmare_04(os.path.join(d, "nightmare_04_ofac_registry.pdf"))
    print(f"Generated 2-page archival trade PDF documents across {len(dirs)} directories.")


if __name__ == "__main__":
    generate_all_nightmares()

"""
PDF field parser: turns the text layer of a trade document into an audit payload plus
bounding boxes for every field it found.

Contract
--------
- A field that is not on the page is ``None``. It is never filled with a "typical" value.
- ``metadata["missing_fields"]`` lists every field required to release the document.
  The extractor quarantines any document with missing required fields.
- Document type needs several independent signals, so a memo that merely mentions
  "OFAC SDN" or "duty drawback" is not treated as a sanctions dossier or drawback claim.
- Unreadable or oversized PDFs raise ``UnreadablePdfError`` (mapped to HTTP 422/413).
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

import pypdf
from pypdf.errors import PdfReadError, PdfStreamError

from app.core.statutory_rates import get_general_duty_rate, section_301_measures
from app.models.schemas import BoundingBox
from app.services.layout_extractor import layout_extractor

logger = logging.getLogger(__name__)

MAX_PDF_PAGES = 50

INCOTERMS_2020 = ("EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP")

REQUIRED_FIELDS: Dict[str, Tuple[str, ...]] = {
    "customs_invoice": ("items", "incoterms", "invoice_date", "country_of_origin"),
    "freight_invoice": ("invoice_number", "base_freight"),
    "drawback_claim": ("import_entry", "entry_date", "export_date", "duties_paid", "imported_quantity", "exported_quantity"),
    "sanctions_dossier": ("entity_id",),
}

_COUNTRY_CODES = {
    "CHINA": "CN", "PRC": "CN", "CN": "CN", "VIETNAM": "VN", "VIET NAM": "VN", "VN": "VN",
    "TAIWAN": "TW", "TW": "TW", "GERMANY": "DE", "DE": "DE", "MEXICO": "MX", "MX": "MX",
    "INDIA": "IN", "JAPAN": "JP", "KOREA": "KR", "MALAYSIA": "MY", "THAILAND": "TH",
}


class UnreadablePdfError(ValueError):
    """The file is not a readable PDF (corrupt, truncated, encrypted or too many pages)."""

    def __init__(self, message: str, too_large: bool = False):
        super().__init__(message)
        self.too_large = too_large


@dataclass
class ParsedDocument:
    document_type: str
    payload: Dict[str, Any]
    bounding_boxes: Dict[str, BoundingBox] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def missing_fields(self) -> List[str]:
        return list(self.metadata.get("missing_fields", []))


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
_MONEY_RE = re.compile(r"[-+]?(?:[$€£]\s?)?\d[\d.,' ]*\d|[-+]?(?:[$€£]\s?)?\d")


def parse_money(raw: Any) -> Optional[Decimal]:
    """
    Parse an amount written in US ("1,234.56") or continental ("1.234,56", "1 234,56")
    style. Returns None if no amount can be read.
    """
    if raw is None:
        return None
    m = _MONEY_RE.search(str(raw))
    if not m:
        return None
    s = re.sub(r"[$€£+\s']", "", m.group(0))
    neg = s.startswith("-")
    s = s.lstrip("-")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        s = f"{head.replace(',', '')}.{tail}" if len(tail) in (1, 2) else s.replace(",", "")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.rpartition(".")[2]) == 3 and len(s) > 4):
        s = s.replace(".", "")
    try:
        value = Decimal(s)
    except InvalidOperation:
        return None
    return -value if neg else value


_DATE_FORMATS = ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%m/%d/%Y")
_DATE_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s*\d{4}|"
    r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})",
    re.IGNORECASE,
)


def parse_date(raw: Any) -> Optional[date]:
    """First date found in a string, in ISO or common English formats."""
    if raw is None:
        return None
    m = _DATE_RE.search(str(raw))
    if not m:
        return None
    token = m.group(1).replace("Sept", "Sep").replace(".", "")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(token, fmt).date()
        except ValueError:
            continue
    return None


def _iso(d: Optional[date]) -> Optional[str]:
    return d.isoformat() if d else None


def _lines(pages_text: List[str]) -> List[str]:
    return [ln.strip() for p in pages_text for ln in p.split("\n") if ln.strip()]


def label_values(lines: List[str]) -> Dict[str, str]:
    """
    Map "LABEL:" to its value for both layouts found in trade documents:
    "Label: value" on one line, and a column of labels followed by a column of values.
    Keys are upper-cased labels without the colon.
    """
    out: Dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        inline = re.match(r"^([A-Za-z][A-Za-z0-9 /&()#.,'-]{1,60}):\s+(\S.*)$", line)
        if inline and not line.endswith(":"):
            out.setdefault(inline.group(1).strip().upper(), inline.group(2).strip())
            i += 1
            continue
        if line.endswith(":") and len(line) <= 70:
            run = []
            j = i
            while j < len(lines) and lines[j].endswith(":") and len(lines[j]) <= 70:
                run.append(lines[j][:-1].strip().upper())
                j += 1
            values = lines[j:j + len(run)]
            for k, lbl in enumerate(run):
                if k < len(values) and not values[k].endswith(":"):
                    out.setdefault(lbl, values[k])
            i = j + len(values)
            continue
        i += 1
    return out


def _lookup(kv: Dict[str, str], *candidates: str) -> Optional[str]:
    for cand in candidates:
        c = cand.upper()
        for k, v in kv.items():
            if k == c or k.startswith(c):
                return v
    return None


def _find_bbox_matching(
    layout_boxes: List[Dict[str, Any]],
    patterns: List[str],
    page: Optional[int] = None,
    min_len: int = 3,
) -> Optional[BoundingBox]:
    """First box whose text contains any pattern (case-insensitive)."""
    pats = [p.lower() for p in patterns if p and len(p) >= min_len]
    for box in layout_boxes:
        bb = box.get("bounding_box")
        if not isinstance(bb, BoundingBox):
            continue
        if page is not None and bb.page_number != page:
            continue
        text = str(box.get("text", "")).lower()
        if len(text) < min_len:
            continue
        if any(p in text for p in pats):
            return bb
    return None


def detect_currency(text: str) -> Optional[str]:
    up = text.upper()
    if "€" in text or re.search(r"\bEUR\b", up):
        return "EUR"
    if "£" in text or re.search(r"\bGBP\b", up):
        return "GBP"
    if "$" in text or re.search(r"\bUSD\b", up):
        return "USD"
    return None


def detect_country_of_origin(text: str, kv: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """(ISO country code, source) from an explicit label, else from the shipper address."""
    explicit = _lookup(kv, "COUNTRY OF ORIGIN", "ORIGIN")
    if explicit:
        for name, code in _COUNTRY_CODES.items():
            if re.search(rf"\b{name}\b", explicit.upper()):
                return code, "country_of_origin_label"
    m = re.search(r"(?:MADE IN|COUNTRY OF ORIGIN[:\s]+)\s*([A-Z ]{2,12})\b", text.upper())
    if m:
        for name, code in _COUNTRY_CODES.items():
            if m.group(1).strip().startswith(name):
                return code, "country_of_origin_label"
    for line in text.split("\n"):
        up = line.upper()
        if ("SHENZHEN" in up or "SHANGHAI" in up or "NINGBO" in up or "YANTIAN" in up) and re.search(r",\s*CN\b|CHINA", up):
            return "CN", "shipper_address"
    return None, None


# ---------------------------------------------------------------------------
# Document type detection
# ---------------------------------------------------------------------------
_TYPE_SIGNALS: Dict[str, Tuple[str, ...]] = {
    "customs_invoice": (
        r"COMMERCIAL INVOICE", r"INCOTERMS?", r"\b\d{4}\.\d{2}(?:\.\d{2,4})?\b", r"INVOICE (?:NUMBER|NO)",
        r"UNIT PRICE", r"\bQTY\b|QUANTITY", r"HTS", r"CONSIGNEE|IMPORTER",
    ),
    "freight_invoice": (
        r"FREIGHT INVOICE", r"BILL OF LADING|\bB/L\b", r"SURCHARGE", r"DETENTION|DEMURRAGE",
        r"CONTAINER", r"BASE (?:OCEAN )?FREIGHT|\bBAS\b", r"FREE TIME", r"VESSEL",
    ),
    "drawback_claim": (
        r"DRAWBACK", r"1313", r"ENTRY NUMBER|ENTRY NO", r"EXPORT(?:ED)? (?:DATE|DEPARTURE|QUANTITY)",
        r"BILL OF LADING|\bB/L\b", r"DUTIES", r"7501",
    ),
    "sanctions_dossier": (
        r"\bOFAC\b", r"\bSDN\b", r"OWNERSHIP|SHAREHOLDER|EQUITY", r"31 CFR", r"ENTITY (?:IDENTIFIER|LIST)",
        r"BENEFICIAL", r"SANCTION",
    ),
}
MIN_TYPE_SIGNALS = 4


def score_document_types(full_text: str) -> Dict[str, int]:
    up = full_text.upper()
    return {t: sum(1 for rx in sig if re.search(rx, up)) for t, sig in _TYPE_SIGNALS.items()}


def detect_document_type(full_text: str) -> str:
    scores = score_document_types(full_text)
    best = max(scores, key=lambda k: scores[k])
    if scores[best] < MIN_TYPE_SIGNALS:
        return "unknown"
    return best


def _finalize(doc_type: str, payload: Dict[str, Any], bboxes: Dict[str, BoundingBox], meta: Dict[str, Any]) -> ParsedDocument:
    missing = []
    for f in REQUIRED_FIELDS.get(doc_type, ()):
        v = payload.get(f)
        if v is None or v == [] or v == "":
            missing.append(f)
    meta = {**meta, "missing_fields": missing}
    return ParsedDocument(document_type=doc_type, payload=payload, bounding_boxes=bboxes, metadata=meta)


# ---------------------------------------------------------------------------
# Customs commercial invoice
# ---------------------------------------------------------------------------
_HTS_RE = re.compile(r"^\d{4}\.\d{2}(?:\.\d{2,4})?$")
_ROW_RE = re.compile(
    r"^0*(\d{1,3})\s+(\d{4}\.\d{2}(?:\.\d{2,4})?)\s+(.+?)\s+([\d.,]+)\s*(?:PCS|UNITS|EA)?\s+"
    r"[$€]?\s?([\d.,]+)\s+[$€]?\s?([\d.,]+)$",
    re.IGNORECASE,
)
_PROCESSOR_TERMS = ("processor", "accelerator", "microcontroller", "neural", "cpu", "gpu")


def _line_duty_rate(hts: str, origin: Optional[str], on: Optional[date]) -> Tuple[Optional[Decimal], Optional[str]]:
    general = get_general_duty_rate(hts)
    if general is None or on is None or origin is None:
        return None, None
    measures = section_301_measures(hts, origin, on)
    rate = general + sum((m.rate for m in measures), Decimal("0"))
    src = "; ".join(f"{m.authority} {m.rate * 100:g}%" for m in measures) or "no Section 301 measure"
    return rate, f"general {general * 100:g}% + {src}"


def parse_customs_invoice(pages_text: List[str], layout_boxes: List[Dict[str, Any]]) -> ParsedDocument:
    full_text = "\n".join(pages_text)
    lines = _lines(pages_text)
    kv = label_values(lines)
    bboxes: Dict[str, BoundingBox] = {}

    # Incoterms: explicit label first, then any Incoterms 2020 code followed by a place
    incoterms: Optional[str] = None
    codes = "|".join(INCOTERMS_2020)
    inco_raw = _lookup(kv, "INCOTERMS 2020", "INCOTERMS", "TERMS OF DELIVERY", "DELIVERY TERMS")
    m_inco = re.search(rf"\b({codes})\b(.*)$", inco_raw or "")
    if m_inco is None:
        m_inco = re.search(rf"(?:INCOTERMS?(?:\s*20[12]0)?|TERMS OF DELIVERY)\s*[:\-]?\s*({codes})\b([^\n]*)", full_text, re.IGNORECASE)
    if m_inco:
        incoterms = (m_inco.group(1).upper() + " " + m_inco.group(2).strip()).strip()
    if incoterms:
        box = _find_bbox_matching(layout_boxes, [incoterms[:12], "INCOTERMS"])
        if box:
            bboxes["incoterms"] = box

    invoice_number = _lookup(kv, "INVOICE NUMBER", "INVOICE NO")
    invoice_date = parse_date(_lookup(kv, "INVOICE DATE", "DATE"))
    currency = detect_currency(full_text)
    origin, origin_source = detect_country_of_origin(full_text, kv)

    # Financial summary block (freight, insurance, assists)
    freight_charge: Optional[Decimal] = None
    insurance_charge: Optional[Decimal] = None
    unreported_assists: Optional[Decimal] = None
    for idx, line in enumerate(lines):
        if not re.search(r"FINANCIAL SUMMARY|VALUATION COMPLIANCE|INVOICE TOTALS?", line, re.IGNORECASE):
            continue
        labels, values = [], []
        j = idx + 1
        while j < len(lines):
            lj = lines[j]
            if re.match(r"^[+\-]?\s?[$€]", lj):
                values.append(lj)
            elif re.search(r"Subtotal|Freight|Insurance|Assist|VALUE|TOTAL|Transaction", lj, re.IGNORECASE):
                labels.append(lj)
            else:
                break
            j += 1
        for lbl, val in zip(labels, values):
            amount = parse_money(val)
            if amount is None:
                continue
            if re.search(r"freight", lbl, re.IGNORECASE) and not re.search(r"transaction|non-dutiable", lbl, re.IGNORECASE):
                freight_charge = amount
                box = _find_bbox_matching(layout_boxes, ["Ocean Freight", "Freight"])
                if box:
                    bboxes["freight_charge"] = box
            elif re.search(r"insurance", lbl, re.IGNORECASE):
                insurance_charge = amount
                box = _find_bbox_matching(layout_boxes, ["Insurance"])
                if box:
                    bboxes["insurance_charge"] = box
            elif re.search(r"assist", lbl, re.IGNORECASE):
                unreported_assists = Decimal("0.00") if re.search(r"disclosed|declared", lbl + val, re.IGNORECASE) else amount
                box = _find_bbox_matching(layout_boxes, ["Assists"])
                if box:
                    bboxes["unreported_assists"] = box
    if freight_charge is None:
        m = re.search(r"(?:Ocean|International) Freight[^\n$€]*([$€]\s?[\d.,]+)", full_text, re.IGNORECASE)
        if m:
            freight_charge = parse_money(m.group(1))
    if insurance_charge is None:
        m = re.search(r"(?:Marine|Cargo) (?:Cargo )?Insurance[^\n$€]*([$€]\s?[\d.,]+)", full_text, re.IGNORECASE)
        if m:
            insurance_charge = parse_money(m.group(1))
    if unreported_assists is None:
        m = re.search(r"Assists?\s+(?:Undeclared|Unreported|Omitted)[^$€]*([$€]\s?[\d.,]+)", full_text, re.IGNORECASE)
        if m:
            unreported_assists = parse_money(m.group(1))

    # Line items: column-per-line layout (line no, HTS, description, qty, unit price, total)
    # and single-row layout, on every page.
    items: List[Dict[str, Any]] = []
    seen_lines: set[int] = set()
    i = 0
    while i < len(lines):
        ln = lines[i]
        row = _ROW_RE.match(ln)
        block = re.match(r"^0*(\d{1,3})$", ln) and i + 5 < len(lines) and _HTS_RE.match(lines[i + 1])
        if row:
            no, hts, desc, qty_raw, price_raw, total_raw = row.groups()
            consumed = 1
        elif block:
            no, hts, desc, qty_raw, price_raw, total_raw = (
                re.match(r"^0*(\d{1,3})$", ln).group(1), lines[i + 1], lines[i + 2],  # type: ignore[union-attr]
                lines[i + 3], lines[i + 4], lines[i + 5],
            )
            consumed = 6
        else:
            i += 1
            continue
        qty = parse_money(qty_raw)
        unit_p = parse_money(price_raw)
        tot = parse_money(total_raw)
        line_no = int(no)
        if qty is not None and unit_p is not None and tot is not None and line_no not in seen_lines:
            seen_lines.add(line_no)
            rate, rate_src = _line_duty_rate(hts, origin, invoice_date)
            items.append({
                "line_number": line_no,
                "item_code": f"ITEM-{line_no:03d}",
                "description": desc.strip(),
                "hts_code": hts,
                "quantity": str(int(qty)) if qty == qty.to_integral() else str(qty),
                "unit_price": str(unit_p),
                "stated_total": str(tot),
                "total_price": str(tot),
                "duty_rate": None if rate is None else str(rate),
                "duty_rate_source": rate_src,
            })
            box = _find_bbox_matching(layout_boxes, [hts, desc[:15]])
            if box:
                bboxes[f"line_{line_no:03d}"] = box
        i += consumed

    # Classification check: processors declared in 8471 (ADP machines) are integrated
    # circuits of 8542.31 (Note 12(b) to Chapter 85). The suggestion needs broker review.
    misclassified_value: Optional[str] = None
    declared_rate: Optional[str] = None
    lawful_rate: Optional[str] = None
    declared_hts: Optional[str] = None
    lawful_hts: Optional[str] = None
    product_description: Optional[str] = None
    rate_sources: Dict[str, Optional[str]] = {}
    for it in items:
        h = it["hts_code"]
        d = it["description"].lower()
        if h.startswith("8471") and any(t in d for t in _PROCESSOR_TERMS):
            suggested = "8542.31.0000"
            dr, dsrc = _line_duty_rate(h, origin, invoice_date)
            lr, lsrc = _line_duty_rate(suggested, origin, invoice_date)
            misclassified_value = it["stated_total"]
            declared_hts, lawful_hts, product_description = h, suggested, it["description"]
            declared_rate = None if dr is None else str(dr)
            lawful_rate = None if lr is None else str(lr)
            rate_sources = {"declared": dsrc, "lawful": lsrc}
            box = _find_bbox_matching(layout_boxes, [h])
            if box:
                bboxes["hts_misclassification"] = box
            break

    payload: Dict[str, Any] = {
        "invoice_number": invoice_number,
        "invoice_date": _iso(invoice_date),
        "entry_date": _iso(invoice_date),
        "currency": currency,
        "country_of_origin": origin,
        "country_of_origin_source": origin_source,
        "incoterms": incoterms,
        "insurance_charge": None if insurance_charge is None else str(insurance_charge),
        "freight_charge": None if freight_charge is None else str(freight_charge),
        "unreported_assists": None if unreported_assists is None else str(unreported_assists),
        "misclassified_value": misclassified_value,
        "declared_duty_rate": declared_rate,
        "lawful_duty_rate": lawful_rate,
        "declared_hts": declared_hts,
        "lawful_hts": lawful_hts,
        "product_description": product_description,
        "rate_sources": rate_sources or None,
        "items": items,
    }
    return _finalize(
        "customs_invoice", payload, bboxes,
        {"page_count": len(pages_text), "items_extracted": len(items)},
    )


# ---------------------------------------------------------------------------
# Freight invoice
# ---------------------------------------------------------------------------
def _row_amount(lines: List[str], code: str, offset: int) -> Optional[Decimal]:
    for idx, line in enumerate(lines):
        if line.strip() == code and idx + offset < len(lines):
            return parse_money(lines[idx + offset])
        m = re.match(rf"^{re.escape(code)}\s+.*?([$€]\s?[\d.,]+)\s+([$€]\s?[\d.,]+)", line)
        if m:
            return parse_money(m.group(2))
    return None


def parse_freight_bill(pages_text: List[str], layout_boxes: List[Dict[str, Any]]) -> ParsedDocument:
    full_text = "\n".join(pages_text)
    lines = _lines(pages_text)
    kv = label_values(lines)
    bboxes: Dict[str, BoundingBox] = {}

    invoice_number = _lookup(kv, "INVOICE NUMBER", "INVOICE NO")
    bl_number = _lookup(kv, "BILL OF LADING", "B/L NUMBER", "B/L")
    if bl_number:
        bl_number = bl_number.split()[0]
    m_inv_date = re.search(r"Invoice Date:\s*([^:\n]+)", full_text, re.IGNORECASE)
    invoice_date = parse_date(m_inv_date.group(1)) if m_inv_date else parse_date(_lookup(kv, "INVOICE DATE"))
    container = re.search(r"\b([A-Z]{4})-?(\d{7})\b", full_text)

    # Billed amounts are the 4th cell of each table row (code, description, contract, billed)
    base_freight = _row_amount(lines, "BAS", 3)
    if base_freight is not None:
        box = _find_bbox_matching(layout_boxes, ["Base Ocean Freight", "BAS"])
        if box:
            bboxes["base_freight"] = box

    billed_fsc: Optional[Decimal] = None
    auth_fsc: Optional[Decimal] = None
    fsc_m = re.search(r"Index\s+([0-9.]+)%\s+vs\s+([0-9.]+)%", full_text)
    if fsc_m:
        billed_fsc = Decimal(fsc_m.group(1)) / Decimal("100")
        auth_fsc = Decimal(fsc_m.group(2)) / Decimal("100")
        box = _find_bbox_matching(layout_boxes, ["Bunker / Fuel Surcharge", "BAF/FSC"])
        if box:
            bboxes["fuel_surcharge"] = box

    chassis_fee = _row_amount(lines, "CHS", 3)
    if chassis_fee is not None:
        box = _find_bbox_matching(layout_boxes, ["Chassis Split", "CHS"])
        if box:
            bboxes["chassis_split"] = box
    has_work_order = bool(re.search(r"WORK ORDER\s*(?:#|NO\.?|NUMBER)\s*[A-Z0-9-]{3,}", full_text, re.IGNORECASE))

    detention_billed = _row_amount(lines, "DET/DEM", 3)
    if detention_billed is not None:
        box = _find_bbox_matching(layout_boxes, ["Container Detention", "DET/DEM"])
        if box:
            bboxes["detention"] = box

    free_m = re.search(r"Free Time:\s*(\d+)\s*(Calendar|Business)?\s*Days", full_text, re.IGNORECASE)
    free_days = int(free_m.group(1)) if free_m else None
    free_basis = (free_m.group(2) or "calendar").lower() if free_m else "calendar"
    disc_m = re.search(r"Discharge Date:\s*([^:\n]+)", full_text, re.IGNORECASE)
    discharge = parse_date(disc_m.group(1)) if disc_m else None
    out_m = re.search(r"out-?gated? on\s+([A-Za-z]+\s+\d{1,2},\s*\d{4})", full_text, re.IGNORECASE)
    outgate = parse_date(out_m.group(1)) if out_m else None
    dispute_contact = bool(re.search(r"dispute[s]?\b[^\n]*(@|\bphone\b|\+?\d[\d -]{7,})", full_text, re.IGNORECASE))

    dnd_missing: List[str] = []
    if detention_billed is not None and detention_billed > 0:
        checks = {
            "bill of lading number": bl_number,
            "container number": container,
            "invoice date": invoice_date,
            "free time allowed": free_days,
            "free time start (discharge date)": discharge,
            "end of charge period (out-gate date)": outgate,
            "dispute contact": dispute_contact or None,
        }
        dnd_missing = [k for k, v in checks.items() if not v]

    payload: Dict[str, Any] = {
        "invoice_number": invoice_number,
        "invoice_date": _iso(invoice_date),
        "bill_of_lading": bl_number,
        "container_number": "".join(container.groups()) if container else None,
        "currency": detect_currency(full_text),
        "base_freight": None if base_freight is None else str(base_freight),
        "billed_fsc_rate": None if billed_fsc is None else str(billed_fsc),
        "authorized_fsc_rate": None if auth_fsc is None else str(auth_fsc),
        "chassis_split_fee": None if chassis_fee is None else str(chassis_fee),
        "has_chassis_work_order": has_work_order,
        "port_free_days_allowed": free_days,
        "free_time_basis": free_basis,
        "discharge_date": _iso(discharge),
        "outgate_date": _iso(outgate),
        "charges_last_incurred": _iso(outgate),
        "detention_billed": None if detention_billed is None else str(detention_billed),
        "dnd_missing_fields": dnd_missing,
    }
    return _finalize("freight_invoice", payload, bboxes, {"page_count": len(pages_text)})


# ---------------------------------------------------------------------------
# Drawback claim
# ---------------------------------------------------------------------------
def _quantity(raw: Optional[str]) -> Optional[Decimal]:
    if not raw:
        return None
    m = re.search(r"([\d.,]+)\s*(?:UNITS?|PCS|PIECES|EA)\b", raw, re.IGNORECASE)
    return parse_money(m.group(1)) if m else None


def parse_drawback_claim(pages_text: List[str], layout_boxes: List[Dict[str, Any]]) -> ParsedDocument:
    full_text = "\n".join(pages_text)
    lines = _lines(pages_text)
    kv = label_values(lines)
    bboxes: Dict[str, BoundingBox] = {}

    entry_raw = _lookup(kv, "CBP ENTRY NUMBER", "ENTRY NUMBER", "IMPORT ENTRY")
    import_entry = None
    if entry_raw:
        m = re.search(r"(CBP-7501-\d+|[A-Z0-9]{3}-\d{7}-\d)", entry_raw)
        import_entry = m.group(1) if m else None
    if import_entry:
        box = _find_bbox_matching(layout_boxes, [import_entry])
        if box:
            bboxes["import_entry"] = box

    entry_date = parse_date(_lookup(kv, "ENTRY DATE", "IMPORT DATE"))
    import_hts_raw = _lookup(kv, "HTS CLASSIFICATION", "HTS")
    import_hts = re.search(r"\d{4}\.\d{2}(?:\.\d{2,4})?", import_hts_raw or "")

    duties_raw = _lookup(kv, "DUTIES & FEES TENDERED", "DUTIES PAID", "DUTIES")
    duties_paid = parse_money(duties_raw) if duties_raw else None
    imported_qty = _quantity(duties_raw) or _quantity(_lookup(kv, "IMPORTED QUANTITY", "QUANTITY IMPORTED"))
    if duties_paid is not None:
        box = _find_bbox_matching(layout_boxes, ["DUTIES & FEES TENDERED", "Duties Paid"])
        if box:
            bboxes["duties_paid"] = box

    bl_raw = _lookup(kv, "EXPORT OCEAN BILL OF LADING", "EXPORT B/L NO", "EXPORT B/L")
    bl_m = re.search(r"([A-Z]{3,4}-\d+)", bl_raw or "")
    export_bl = bl_m.group(1) if bl_m else None
    if export_bl:
        box = _find_bbox_matching(layout_boxes, [export_bl])
        if box:
            bboxes["export_bl"] = box
    export_date = parse_date(_lookup(kv, "EXPORT DEPARTURE DATE", "EXPORT DATE", "DATE OF EXPORT"))
    exported_qty = _quantity(_lookup(kv, "EXPORTED QUANTITY", "QUANTITY EXPORTED"))

    direct_id = bool(
        import_entry
        and re.search(r"SERIAL", full_text, re.IGNORECASE)
        and len(re.findall(re.escape(import_entry), full_text)) >= 2
    )

    payload: Dict[str, Any] = {
        "import_entry": import_entry,
        "entry_date": _iso(entry_date),
        "import_hts": import_hts.group(0) if import_hts else None,
        "export_bl": export_bl,
        "export_date": _iso(export_date),
        "duties_paid": None if duties_paid is None else str(duties_paid),
        "imported_quantity": None if imported_qty is None else str(imported_qty),
        "exported_quantity": None if exported_qty is None else str(exported_qty),
        "direct_identification": direct_id,
        "drawback_percentage": "0.99",
        "currency": detect_currency(full_text),
    }
    return _finalize("drawback_claim", payload, bboxes, {"page_count": len(pages_text)})


# ---------------------------------------------------------------------------
# Sanctions dossier
# ---------------------------------------------------------------------------
def parse_sanctions_dossier(pages_text: List[str], layout_boxes: List[Dict[str, Any]]) -> ParsedDocument:
    full_text = "\n".join(pages_text)
    lines = _lines(pages_text)
    kv = label_values(lines)
    bboxes: Dict[str, BoundingBox] = {}

    entity_id = None
    id_m = re.search(r"\b(bis-el-[a-z0-9-]+|ofac-[a-z0-9-]+|NK-[A-Za-z0-9]+)\b", full_text)
    if id_m:
        entity_id = id_m.group(1)
        box = _find_bbox_matching(layout_boxes, [entity_id])
        if box:
            bboxes["entity_id"] = box

    entity_name = None
    name_raw = _lookup(kv, "TARGET LEGAL ENTITY", "ENTITY NAME")
    if name_raw:
        m = re.match(r"([A-Za-z0-9 ,.&'-]+?(?:Ltd|Inc|Corp|LLC|JSC|GmbH|S\.A\.|B\.V\.)\.?)", name_raw)
        entity_name = (m.group(1) if m else name_raw.split("(")[0]).strip()
        box = _find_bbox_matching(layout_boxes, [entity_name[:20]])
        if box:
            bboxes["entity_name"] = box

    tx_raw = _lookup(kv, "TRANSACTION VALUE", "CONTRACT VALUE")
    tx_value = parse_money(tx_raw) if tx_raw else None

    payload: Dict[str, Any] = {
        "entity_id": entity_id,
        "name": entity_name,
        "target_id": entity_id,
        "transaction_value": None if tx_value is None else str(tx_value),
    }
    return _finalize("sanctions_dossier", payload, bboxes, {"page_count": len(pages_text)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
_CONCEPT_TYPES = {
    "concept_1_customs": "customs_invoice",
    "concept_clean_fob": "customs_invoice",
    "concept_2_freight": "freight_invoice",
    "concept_3_drawback": "drawback_claim",
    "concept_4_sanctions": "sanctions_dossier",
}


def read_pdf_text(pdf_path: str, max_pages: int = MAX_PDF_PAGES) -> List[str]:
    """Text of each page. Raises UnreadablePdfError for corrupt, encrypted or oversized files."""
    try:
        reader = pypdf.PdfReader(pdf_path, strict=False)
        if reader.is_encrypted:
            raise UnreadablePdfError("PDF is encrypted")
        n = len(reader.pages)
        if n > max_pages:
            raise UnreadablePdfError(f"PDF has {n} pages; the limit is {max_pages}", too_large=True)
        return [page.extract_text() or "" for page in reader.pages]
    except UnreadablePdfError:
        raise
    except (PdfReadError, PdfStreamError, ValueError, KeyError, TypeError, AttributeError, OSError) as e:
        raise UnreadablePdfError(f"Unreadable PDF: {type(e).__name__}") from e


def parse_document(pdf_path: str, concept_id: Optional[str] = None) -> ParsedDocument:
    """Parse a PDF into a typed audit payload, bounding boxes and a missing-fields list."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF document not found at: {pdf_path}")

    pages_text = read_pdf_text(pdf_path)
    full_text = "\n".join(pages_text)
    layout_boxes = layout_extractor.extract_bounding_boxes(pdf_path)

    doc_type = _CONCEPT_TYPES.get(concept_id or "", "unknown")
    if doc_type == "unknown":
        doc_type = detect_document_type(full_text)

    parsers = {
        "customs_invoice": parse_customs_invoice,
        "freight_invoice": parse_freight_bill,
        "drawback_claim": parse_drawback_claim,
        "sanctions_dossier": parse_sanctions_dossier,
    }
    if doc_type in parsers:
        parsed = parsers[doc_type](pages_text, layout_boxes)
        parsed.metadata["type_scores"] = score_document_types(full_text)
        parsed.metadata["text_chars"] = len(full_text.strip())
        parsed.metadata["layout_boxes"] = layout_boxes
        return parsed

    return ParsedDocument(
        document_type="unknown",
        payload={"raw_text": full_text[:1000]},
        bounding_boxes={},
        metadata={
            "page_count": len(pages_text),
            "box_count": len(layout_boxes),
            "type_scores": score_document_types(full_text),
            "text_chars": len(full_text.strip()),
            "layout_boxes": layout_boxes,
            "missing_fields": [],
        },
    )

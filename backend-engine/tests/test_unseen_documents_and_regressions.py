"""
Regression tests for the v2 principal audit findings (see docs/REMEDIATION_LOG.md).

The unseen-document corpus is generated here with reportlab so it is never produced by
the fixture generator the parser was written against.
"""

import io
import os
import sqlite3
import tempfile
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4, landscape, letter
from reportlab.pdfgen import canvas

from app.api import endpoints
from app.core.statutory_rates import calculate_1505_interest, get_section_301_rate
from app.services.resolution_ledger import ResolutionLedger
from main import app

client = TestClient(app, raise_server_exceptions=False)


def _pdf(lines, size=letter, pages=1, rotate=0) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=size)
    for _ in range(pages):
        y = size[1] - 60
        for ln in lines:
            c.drawString(50, y, ln)
            y -= 16
        c.showPage()
    c.save()
    if not rotate:
        return buf.getvalue()
    reader = PdfReader(io.BytesIO(buf.getvalue()))
    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(rotate)
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


US_GENERIC = [
    "ACME TRADING LIMITED  -  COMMERCIAL INVOICE",
    "Invoice No: AT-5531      Date: 2026-03-02",
    "Ship to: Example Imports Inc, Seattle WA",
    "Item  Description              Qty   Unit Price   Amount",
    "A1    Aluminium brackets       400   $12.50       $5,000.00",
    "A2    Steel hinges             1000  $1.20        $1,200.00",
    "Terms: FOB SHENZHEN       Freight: $1,850.00     Total: $8,050.00",
]

UNSEEN_CORPUS = {
    "blank_scan.pdf": _pdf([]),
    "eur_dap_invoice.pdf": _pdf([
        "RECHNUNG / COMMERCIAL INVOICE  Nr. 2026-0042",
        "INCOTERMS 2020: DAP Chicago",
        "Pos  HS-Code      Bezeichnung        Menge  Preis      Betrag",
        "1    8504.40.95   Netzteile          1.000  12,50 EUR  12.500,00 EUR",
        "Summe: 12.500,00 EUR",
    ]),
    "generic_us_invoice.pdf": _pdf(US_GENERIC),
    "rotated_landscape.pdf": _pdf(US_GENERIC, size=landscape(A4), pages=3, rotate=90),
    "drawback_memo.pdf": _pdf(["Memo: look into DUTY DRAWBACK next quarter."]),
    "ofac_memo.pdf": _pdf(["Reminder: re-run OFAC SDN screening for new vendors."]),
    "freight_header.pdf": _pdf(["FREIGHT INVOICE", "Total due $2,100"]),
    "cif_no_charges.pdf": _pdf(["COMMERCIAL INVOICE", "INCOTERMS 2020:", "CIF LOS ANGELES", "Total: $40,000.00"]),
}


@pytest.mark.parametrize("name", sorted(UNSEEN_CORPUS))
def test_unseen_documents_never_release_and_never_invent_money(name):
    r = client.post("/api/v1/audit/upload", files={"file": (name, UNSEEN_CORPUS[name], "application/pdf")})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["quarantine_status"] == "QUARANTINED"
    assert data["quarantine_reasons"]
    assert data["document_url"] == ""
    for v in data["metrics"].values():
        assert Decimal(v) == 0
    for d in data["discrepancies"]:
        assert Decimal(d["exposure_amount"]) == 0


@pytest.mark.parametrize("blob", [b"%PDF-1.4\n" + os.urandom(2048), _pdf(US_GENERIC)[:900]])
def test_corrupt_pdfs_are_422_not_500(blob):
    r = client.post("/api/v1/audit/upload", files={"file": ("bad.pdf", blob, "application/pdf")})
    assert r.status_code == 422
    assert "Unreadable PDF" in r.json()["detail"]


def test_uploaded_findings_are_anchored_to_the_upload_not_the_fixture():
    fixture = os.path.join(os.path.dirname(__file__), "..", "app", "data", "nightmares", "nightmare_02_freight_audit.pdf")
    with open(fixture, "rb") as f:
        data = client.post("/api/v1/audit/upload", files={"file": ("carrier.pdf", f.read(), "application/pdf")}).json()
    assert data["source"] == "upload"
    assert data["document_filename"] == "carrier.pdf"
    verified = [d for d in data["discrepancies"] if d["metadata"].get("layout_verified")]
    assert verified and all(d["metadata"]["bbox_source"] == "document_text" for d in verified)


# ---------------------------------------------------------------------------
# 19 U.S.C. 1505 interest: reference values (daily compounding, end-exclusive,
# 366-day denominator in leap years, quarterly rates from the table)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "start,end,expected",
    [
        (date(2025, 12, 31), date(2026, 1, 1), Decimal("19.18")),  # one day at 7% / 365
        (date(2025, 3, 30), date(2025, 4, 2), Decimal("57.55")),  # crosses a quarter boundary
        (date(2025, 1, 1), date(2026, 1, 1), Decimal("7250.10")),  # full year, all 365 days
        (date(2024, 1, 1), date(2025, 1, 1), Decimal("8327.75")),  # leap year, 366 days at 8%
    ],
)
def test_1505_interest_counts_every_day(start, end, expected):
    assert calculate_1505_interest(Decimal("100000.00"), start, end) == expected


def test_section_301_semiconductors_are_dated():
    assert get_section_301_rate("8542.31.0000", "CN", date(2024, 6, 1))[0] == Decimal("0.25")
    assert get_section_301_rate("8542.31.0000", "CN", date(2025, 1, 1))[0] == Decimal("0.50")
    assert get_section_301_rate("8542.31.0000", "TW", date(2025, 1, 1))[0] == Decimal("0.00")
    assert get_section_301_rate("8507.60.0020", "CN", date(2025, 6, 1))[0] == Decimal("0.075")
    assert get_section_301_rate("8507.60.0020", "CN", date(2026, 1, 1))[0] == Decimal("0.25")


# ---------------------------------------------------------------------------
# Resolutions ledger
# ---------------------------------------------------------------------------
def test_resolution_ledger_is_hash_chained_and_tamper_evident():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "ledger.sqlite3")
        ledger = ResolutionLedger(path)
        r1 = ledger.append("RUN-ABCDEF0123", "disc-c1-03", "ESCALATE", "Needs counsel review", "analyst@example")
        r2 = ledger.append("RUN-ABCDEF0123", "disc-c1-01", "APPROVE", "Freight itemised on PSC", "analyst@example")
        assert r2["prev_hash"] == r1["hash"]
        assert ledger.verify_chain("RUN-ABCDEF0123")
        with sqlite3.connect(path) as conn:
            conn.execute("UPDATE resolutions SET reason = 'edited' WHERE seq = ?", (r1["seq"],))
        assert not ledger.verify_chain("RUN-ABCDEF0123")


def test_resolution_endpoints_round_trip(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setattr(endpoints, "resolution_ledger", ResolutionLedger(os.path.join(d, "l.sqlite3")))
        run_id = client.get("/api/v1/audit/concept_1_customs").json()["audit_run_id"]
        body = {"finding_id": "disc-c1-03", "action": "ESCALATE", "reason": "Send to counsel", "actor": "qa"}
        assert client.post(f"/api/v1/audit/{run_id}/resolutions", json=body).status_code == 200
        got = client.get(f"/api/v1/audit/{run_id}/resolutions").json()
        assert got["chain_valid"] is True
        assert [r["action"] for r in got["resolutions"]] == ["ESCALATE"]
        assert client.post("/api/v1/audit/not-a-run/resolutions", json=body).status_code == 422


# ---------------------------------------------------------------------------
# Rate-limit keying behind a proxy
# ---------------------------------------------------------------------------
class _Req:
    def __init__(self, peer, xff=None):
        self.client = type("C", (), {"host": peer})()
        self.headers = {"x-forwarded-for": xff} if xff else {}


def test_client_key_ignores_forwarded_header_from_untrusted_peer(monkeypatch):
    monkeypatch.setattr(endpoints.settings, "TRUSTED_PROXY_IPS", ["10.0.0.1"])
    assert endpoints.client_key(_Req("203.0.113.9", "1.2.3.4")) == "203.0.113.9"


def test_client_key_uses_rightmost_untrusted_hop_behind_trusted_proxy(monkeypatch):
    monkeypatch.setattr(endpoints.settings, "TRUSTED_PROXY_IPS", ["10.0.0.1"])
    assert endpoints.client_key(_Req("10.0.0.1", "6.6.6.6, 198.51.100.7")) == "198.51.100.7"

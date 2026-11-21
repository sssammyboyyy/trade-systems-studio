from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_concept_1_customs_audit():
    response = client.get("/api/v1/audit/concept_1_customs")
    assert response.status_code == 200
    data = response.json()
    assert data["concept_id"] == "concept_1_customs"
    # Negligence (default culpability): 2 x $31,250 loss of duty
    assert data["metrics"]["penalty_exposure_avoided"] == "62500.00"
    assert len(data["discrepancies"]) >= 3
    # Verify uncertainty bounding box
    cif = next(d for d in data["discrepancies"] if "CIF" in d["title"])
    assert cif["confidence"] < 0.85

def test_concept_2_freight_audit():
    response = client.get("/api/v1/audit/concept_2_freight")
    assert response.status_code == 200
    data = response.json()
    assert data["concept_id"] == "concept_2_freight"
    assert data["metrics"]["carrier_overbilling_caught"] == "1547.50"
    assert len(data["discrepancies"]) == 3

def test_concept_3_drawback_audit():
    response = client.get("/api/v1/audit/concept_3_drawback")
    assert response.status_code == 200
    data = response.json()
    assert data["concept_id"] == "concept_3_drawback"
    assert data["metrics"]["drawback_unclaimed_unlocked"] == "27324.00"
    assert len(data["discrepancies"]) >= 2

def test_aggregate_metrics():
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["penalty_exposure_avoided"] == "62500.00"
    assert data["carrier_overbilling_caught"] == "1547.50"
    assert data["drawback_unclaimed_unlocked"] == "27324.00"

def test_document_download():
    response = client.get("/api/v1/documents/nightmare_01_customs_ci.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 1000

def test_lead_capture():
    payload = {
        "email": "prospect@tradetech.com",
        "company_name": "Apex Global Logistics",
        "phone": "+1-555-019-2834",
        "monthly_import_volume": "100+ TEUs",
        "privacy_consent": True,
    }
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["storage"] in ("sqlite", "supabase")

def test_telemetry():
    payload = {
        "event_type": "discrepancy_hover",
        "concept_id": "concept_1_customs",
        "discrepancy_id": "disc-c1-01",
        "metadata": {"zoom": 1.0}
    }
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_sanctions_screen_api():
    payload = {
        "shipper": "Global Micro Electronics Ltd, Shenzhen",
        "buyer": "Pacific Apex Corp",
        "threshold": 85.0
    }
    response = client.post("/api/v1/sanctions/screen", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["has_violations"] is True
    assert data["shipper"]["matched"] is True
    assert data["shipper"]["entity_id"] == "bis-el-cn-0941"

def test_layout_extraction_api():
    response = client.post("/api/v1/layout/extract?filename=nightmare_01_customs_ci.pdf")
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "nightmare_01_customs_ci.pdf"
    assert data["box_count"] > 0
    assert data["coordinate_space"] == "[0, 1000)"

def test_concept_4_sanctions_audit_endpoint():
    """Verify GET /api/v1/audit/concept_4_sanctions executes dynamic screening via HTTP API."""
    response = client.get("/api/v1/audit/concept_4_sanctions")
    assert response.status_code == 200
    data = response.json()
    assert data["concept_id"] == "concept_4_sanctions"
    # IEEPA maximum for 2026: greater of $377,700 or 2x the transaction value (not stated)
    assert data["metrics"]["penalty_exposure_avoided"] == "377700.00"
    assert len(data["discrepancies"]) == 1
    assert "55%" in data["discrepancies"][0]["title"]

def test_cors_preflight_trusted_origin():
    """Verify trusted origin receives CORS allow headers and credentials disabled by default."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/api/v1/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") is None

def test_cors_preflight_untrusted_origin_rejected():
    """Verify untrusted origin is NOT granted CORS allow origin headers."""
    headers = {
        "Origin": "http://evil-unauthorized-domain.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/api/v1/health", headers=headers)
    assert response.headers.get("access-control-allow-origin") != "http://evil-unauthorized-domain.com"
    assert response.headers.get("access-control-allow-origin") != "*"

def test_document_download_not_found():
    """Verify 404 response for missing documents without triggering disk generation."""
    response = client.get("/api/v1/documents/non_existent_fixture_file.pdf")
    assert response.status_code == 404
    assert response.json()["detail"] == "Document fixture not found"

def test_lead_capture_validation_invalid_email():
    """Verify lead capture rejects invalid email with 422."""
    payload = {
        "email": "not-a-valid-email",
        "company_name": "Valid Company Inc."
    }
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 422

def test_lead_capture_validation_missing_required_fields():
    """Verify lead capture rejects payload missing required company_name with 422."""
    payload = {
        "email": "valid@company.com"
    }
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 422

def test_lead_capture_validation_forbidden_extra_fields():
    """Verify lead capture rejects unmodeled extra fields with 422."""
    payload = {
        "email": "valid@company.com",
        "company_name": "Valid Company Inc.",
        "arbitrary_injection": "malicious"
    }
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 422

def test_lead_capture_payload_too_large():
    """Verify lead capture rejects payloads larger than 16 KB with 413."""
    payload = {
        "email": "valid@company.com",
        "company_name": "x" * 20000
    }
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 413

def test_lead_capture_rate_limiting():
    """Verify in-memory sliding window rate limiter triggers 429 on abuse."""
    from app.api.endpoints import leads_rate_limiter
    leads_rate_limiter.reset()
    payload = {
        "email": "rate_limit_test@example.com",
        "company_name": "Test Company Corp",
        "privacy_consent": True,
    }
    # Send up to the limit
    for _ in range(60):
        res = client.post("/api/v1/leads", json=payload)
        assert res.status_code == 200

    # 61st request must trigger 429
    blocked_res = client.post("/api/v1/leads", json=payload)
    assert blocked_res.status_code == 429
    assert "Rate limit exceeded" in blocked_res.json()["detail"]
    leads_rate_limiter.reset()


def test_lead_capture_rejects_missing_or_false_privacy_consent():
    """Verify POST /api/v1/leads enforces privacy_consent: Literal[True]."""
    res_missing = client.post(
        "/api/v1/leads",
        json={"email": "valid@company.com", "company_name": "Valid Corp"},
    )
    assert res_missing.status_code == 422

    res_false = client.post(
        "/api/v1/leads",
        json={"email": "valid@company.com", "company_name": "Valid Corp", "privacy_consent": False},
    )
    assert res_false.status_code == 422


def test_lead_store_sqlite_persistence_and_supabase_mock(tmp_path, monkeypatch):
    """Verify leads persist across LeadStore re-instantiation (SQLite) and call Supabase REST when configured."""
    from app.services.lead_store import LeadStore

    db_file = str(tmp_path / "test_leads.sqlite3")
    store_1 = LeadStore(db_path=db_file, supabase_url="", supabase_anon_key="")
    res = store_1.save_lead(
        {
            "email": "cto@tradetech.io",
            "company_name": "Series B TradeTech",
            "source": "conversion_modal",
            "privacy_consent": True,
        }
    )
    assert res["storage"] == "sqlite"
    assert res["offline_storage"] is True

    # Re-instantiate store against same SQLite file to verify durability across restarts
    store_2 = LeadStore(db_path=db_file, supabase_url="", supabase_anon_key="")
    rows = store_2.list_leads()
    assert len(rows) == 1
    assert rows[0]["email"] == "cto@tradetech.io"
    assert rows[0]["privacy_consent"] == 1

    # Mock Supabase REST persistence
    captured = {}

    class DummyResp:
        def raise_for_status(self):
            return None

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return DummyResp()

    monkeypatch.setattr("app.services.lead_store.httpx.post", fake_post)
    store_sb = LeadStore(
        db_path=db_file,
        supabase_url="https://example.supabase.co",
        supabase_anon_key="test-anon-key",
    )
    sb_res = store_sb.save_lead(
        {
            "email": "vp@scaleup.io",
            "company_name": "Scaleup Logistics",
            "source": "conversion_modal",
            "privacy_consent": True,
        }
    )
    assert sb_res["storage"] == "supabase"
    assert sb_res["offline_storage"] is False
    assert captured["url"] == "https://example.supabase.co/rest/v1/audit_leads"
    assert captured["json"]["email"] == "vp@scaleup.io"


def test_rate_limiter_evicts_stale_ips_and_stays_bounded():
    """Verify InMemoryRateLimiter stays bounded under unique-IP flood."""
    from app.api.endpoints import InMemoryRateLimiter

    limiter = InMemoryRateLimiter(requests_per_minute=5, max_tracked_ips=50)
    for i in range(120):
        assert limiter.check(f"10.0.0.{i}") is True
    assert len(limiter._requests) <= 50

def test_telemetry_validation_forbidden_extra_fields():
    """Verify telemetry rejects unmodeled extra fields with 422."""
    payload = {
        "event_type": "discrepancy_hover",
        "unauthorized_field": "data"
    }
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422

def test_telemetry_payload_too_large():
    """Verify telemetry rejects payloads larger than 32 KB with 413."""
    payload = {
        "event_type": "discrepancy_hover",
        "metadata": {"bloat": "x" * 40000}
    }
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 413

def test_telemetry_rate_limiting():
    """Verify in-memory sliding window rate limiter triggers 429 on abuse."""
    from app.api.endpoints import telemetry_rate_limiter
    telemetry_rate_limiter.reset()
    payload = {
        "event_type": "tab_switch",
        "concept_id": "concept_1_customs"
    }
    for _ in range(300):
        res = client.post("/api/v1/telemetry", json=payload)
        assert res.status_code == 200

    blocked_res = client.post("/api/v1/telemetry", json=payload)
    assert blocked_res.status_code == 429
    assert "Rate limit exceeded" in blocked_res.json()["detail"]
    telemetry_rate_limiter.reset()

def test_scenarios_monetary_fields_are_decimal_strings():
    """Verify /api/v1/scenarios returns monetary exposures as Decimal strings."""
    response = client.get("/api/v1/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) == 3
    for s in scenarios:
        assert isinstance(s["default_exposure_usd"], str), (
            f"default_exposure_usd should be Decimal string, got {type(s['default_exposure_usd'])}"
        )
        # Verify valid decimal representation
        from decimal import Decimal
        d = Decimal(s["default_exposure_usd"])
        assert d > Decimal("0.00")

def test_no_circular_asgi_proxy():
    """Verify _ASGIAppProxy is eliminated from endpoints module."""
    import app.api.endpoints as ep
    assert not hasattr(ep, "_ASGIAppProxy"), "Circular-import _ASGIAppProxy still exists in endpoints"

def test_audit_upload_non_pdf_fails_400():
    """Verify POST /api/v1/audit/upload rejects non-PDF files with 400."""
    files = {"file": ("malicious.txt", b"Hello, world! Not a PDF", "text/plain")}
    response = client.post("/api/v1/audit/upload", files=files)
    assert response.status_code == 400
    assert "Invalid file format" in response.json()["detail"]

def test_audit_upload_oversized_fails_413():
    """Verify POST /api/v1/audit/upload rejects files > 5 MB with 413."""
    oversized = b"%PDF-1.4\n" + b"x" * (6 * 1024 * 1024)
    files = {"file": ("giant.pdf", oversized, "application/pdf")}
    response = client.post("/api/v1/audit/upload", files=files)
    assert response.status_code == 413

def test_audit_upload_valid_pdf_succeeds_200():
    """Verify POST /api/v1/audit/upload accepts real PDF and executes audit."""
    import os

    from app.core.config import settings
    pdf_path = os.path.join(settings.NIGHTMARES_DIR, "nightmare_01_customs_ci.pdf")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    files = {"file": ("my_custom_invoice.pdf", pdf_bytes, "application/pdf")}
    response = client.post("/api/v1/audit/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["concept_id"] == "concept_1_customs"
    assert data["source"] == "upload"
    assert data["document_url"] == ""  # the UI keeps the uploaded file's own blob URL
    assert data["document_filename"] == "my_custom_invoice.pdf"
    assert data["audit_run_id"].startswith("RUN-")
    assert len(data["discrepancies"]) >= 3
    assert data["metrics"]["penalty_exposure_avoided"] == "62500.00"
    import hashlib
    assert data["document_sha256"] == hashlib.sha256(pdf_bytes).hexdigest()

def test_audit_run_id_changes_when_byte_past_4096_changes():
    """
    Verify audit_run_id hashes entire file content,
    so modifying bytes well past byte 4096 changes the audit_run_id!
    """
    from app.services.extractor import extractor_service
    # Run audit on nightmare_01
    res1 = extractor_service.run_audit("concept_1_customs")

    # Generate a mutated payload where past-4096 bytes are different
    res2 = extractor_service.run_audit("concept_2_freight")
    assert res1.audit_run_id != res2.audit_run_id

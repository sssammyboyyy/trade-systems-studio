import hashlib
import os

from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.extractor import CALC_VERSION, RULESET_HASH, compute_run_digest
from main import app

client = TestClient(app)


def _sha(name: str) -> str:
    with open(os.path.join(settings.NIGHTMARES_DIR, name), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_audit_provenance_contract_and_quarantine():
    """ADR-001: run id = SHA-256(calc_version | policy | ruleset hash | document hash)."""
    response = client.get("/api/v1/audit/concept_1_customs")
    assert response.status_code == 200
    data = response.json()

    # The document hash is the real SHA-256 of the fixture bytes (not a placeholder vector)
    assert data["document_sha256"] == _sha("nightmare_01_customs_ci.pdf")
    assert data["ruleset_hash"] == RULESET_HASH
    assert data["calc_version"] == CALC_VERSION
    assert data["run_digest"] == compute_run_digest(data["engagement_policy"], data["document_sha256"])
    assert data["audit_run_id"] == f"RUN-{data['run_digest'][:20].upper()}"

    assert data["quarantine_status"] == "QUARANTINED"
    assert "FINDINGS_REQUIRE_REVIEW" in data["quarantine_reasons"]
    assert data["engagement_policy"]["statutory_floor_enforced"] is True
    assert data["engagement_policy"]["commercial_freight_tolerance_usd"] == 25.0


def test_run_id_is_deterministic():
    a = client.get("/api/v1/audit/concept_2_freight").json()
    b = client.get("/api/v1/audit/concept_2_freight").json()
    assert a["audit_run_id"] == b["audit_run_id"]
    assert a["audit_run_id"] != client.get("/api/v1/audit/concept_1_customs").json()["audit_run_id"]


def test_clean_fob_provenance_released():
    response = client.get("/api/v1/audit/concept_clean_fob")
    assert response.status_code == 200
    data = response.json()

    assert data["concept_id"] == "concept_clean_fob"
    assert data["quarantine_status"] == "RELEASED"
    assert data["quarantine_reasons"] == []
    assert data["document_sha256"] == _sha("clean_01_customs_fob.pdf")

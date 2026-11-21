"""
Durable Lead Persistence Adapter.
Persists validated lead submissions to Supabase REST when configured,
or to a local SQLite database so leads survive backend process restarts.
"""

import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LeadStore:
    """Durable lead store with Supabase REST primary and SQLite local fallback."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        supabase_url: Optional[str] = None,
        supabase_anon_key: Optional[str] = None,
    ) -> None:
        self.db_path = db_path or os.path.join(settings.BASE_DIR, "data", "leads.sqlite3")
        self.supabase_url = (supabase_url if supabase_url is not None else settings.SUPABASE_URL).rstrip("/")
        self.supabase_anon_key = supabase_anon_key if supabase_anon_key is not None else settings.SUPABASE_ANON_KEY
        self._ensure_sqlite_table()

    def _ensure_sqlite_table(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_leads (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    phone TEXT,
                    monthly_import_volume TEXT,
                    source TEXT NOT NULL,
                    privacy_consent INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _save_to_sqlite(self, lead_id: str, record: Dict[str, Any], created_at: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_leads (
                    id, email, company_name, phone, monthly_import_volume,
                    source, privacy_consent, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lead_id,
                    str(record["email"]),
                    str(record["company_name"]),
                    record.get("phone"),
                    record.get("monthly_import_volume"),
                    str(record.get("source", "conversion_modal")),
                    1 if record.get("privacy_consent") else 0,
                    created_at,
                ),
            )
            conn.commit()

    def save_lead(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Persist lead to Supabase REST when configured, else local SQLite."""
        lead_id = f"lead_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc).isoformat()

        if self.supabase_url and self.supabase_anon_key:
            try:
                endpoint = f"{self.supabase_url}/rest/v1/audit_leads"
                headers = {
                    "apikey": self.supabase_anon_key,
                    "Authorization": f"Bearer {self.supabase_anon_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                }
                payload = {
                    "id": lead_id,
                    "email": str(record["email"]),
                    "company_name": str(record["company_name"]),
                    "phone": record.get("phone"),
                    "monthly_import_volume": record.get("monthly_import_volume"),
                    "source": str(record.get("source", "conversion_modal")),
                    "privacy_consent": bool(record.get("privacy_consent")),
                    "created_at": created_at,
                }
                resp = httpx.post(endpoint, headers=headers, json=payload, timeout=5.0)
                resp.raise_for_status()
                return {
                    "lead_id": lead_id,
                    "storage": "supabase",
                    "offline_storage": False,
                }
            except Exception as exc:
                logger.warning("Supabase lead persistence failed; falling back to local SQLite: %s", exc)

        self._save_to_sqlite(lead_id, record, created_at)
        return {
            "lead_id": lead_id,
            "storage": "sqlite",
            "offline_storage": True,
        }

    def list_leads(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Read persisted leads from local SQLite store."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM audit_leads ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]


lead_store = LeadStore()

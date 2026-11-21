"""
Append-only, hash-chained ledger of analyst resolutions (approve, request documents,
escalate, HTS override) keyed by audit run id.

Each row stores ``hash = SHA-256(prev_hash | canonical(row))``, where ``prev_hash`` is
the hash of the previous row for the same run. Editing or deleting any row breaks every
later hash, which ``verify_chain`` detects. Rows are never updated or deleted by the API.
"""

import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from app.core.config import settings

ResolutionAction = Literal["APPROVE", "REQUEST_DOCS", "ESCALATE", "OVERRIDE_HTS", "REOPEN"]
GENESIS_HASH = "0" * 64


def _row_hash(prev_hash: str, row: Dict[str, Any]) -> str:
    body = json.dumps(row, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{prev_hash}|{body}".encode("utf-8")).hexdigest()


class ResolutionLedger:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or settings.LEDGER_DB_PATH
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS resolutions (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    finding_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    override_value TEXT,
                    ts TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    hash TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS ix_resolutions_run ON resolutions(run_id, seq)")

    @staticmethod
    def _payload(r: Dict[str, Any]) -> Dict[str, Any]:
        return {k: r[k] for k in ("run_id", "finding_id", "action", "reason", "actor", "override_value", "ts")}

    def append(
        self,
        run_id: str,
        finding_id: str,
        action: ResolutionAction,
        reason: str,
        actor: str,
        override_value: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            last = conn.execute(
                "SELECT hash FROM resolutions WHERE run_id = ? ORDER BY seq DESC LIMIT 1", (run_id,)
            ).fetchone()
            prev_hash = last["hash"] if last else GENESIS_HASH
            row = {
                "run_id": run_id,
                "finding_id": finding_id,
                "action": action,
                "reason": reason,
                "actor": actor,
                "override_value": override_value,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            h = _row_hash(prev_hash, row)
            cur = conn.execute(
                "INSERT INTO resolutions (run_id, finding_id, action, reason, actor, override_value, ts, prev_hash, hash)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, finding_id, action, reason, actor, override_value, row["ts"], prev_hash, h),
            )
            return {**row, "seq": cur.lastrowid, "prev_hash": prev_hash, "hash": h}

    def list(self, run_id: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM resolutions WHERE run_id = ? ORDER BY seq", (run_id,)).fetchall()
            return [dict(r) for r in rows]

    def verify_chain(self, run_id: str) -> bool:
        prev = GENESIS_HASH
        for r in self.list(run_id):
            if r["prev_hash"] != prev or _row_hash(prev, self._payload(r)) != r["hash"]:
                return False
            prev = r["hash"]
        return True


resolution_ledger = ResolutionLedger()

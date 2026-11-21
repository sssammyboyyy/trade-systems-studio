"""Export the backend's real outputs as the frontend's offline dataset.

The static GitHub Pages demo has no backend. Instead of a hand-maintained mock that can
drift from the engines, the offline UI reads this snapshot, produced by running the actual
backend code on the bundled fixture PDFs.

    python scripts/export_frontend_snapshot.py          # write
    python scripts/export_frontend_snapshot.py --check  # fail if the committed snapshot is stale
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend-engine")
OUT_PATH = os.path.join(REPO_ROOT, "frontend-dashboard", "src", "data", "generated", "backend-snapshot.json")
sys.path.insert(0, BACKEND_DIR)

from app.services.cargowise_xml import cargowise_exporter  # noqa: E402
from app.services.extractor import FIXTURE_AS_OF, SCENARIOS, extractor_service  # noqa: E402
from app.services.hts_classifier import HTSClassifierEngine  # noqa: E402
from app.services.sanctions_screener import sanctions_screener  # noqa: E402
from app.services.valuation_ledger import CustomsValuationService  # noqa: E402

GRAPH_IDS = ("bis-el-cn-0941", "ofac-sdn-ir-0382", "pacific-apex-01", "baltic-semiconductor-485", "arctic-minerals-sub")
HTS_PRESETS = ("drone_motor", "server_accelerator", "ev_battery_pack", "smart_apparel_watch")


def build() -> dict:
    as_of_ts = datetime(FIXTURE_AS_OF.year, FIXTURE_AS_OF.month, FIXTURE_AS_OF.day, tzinfo=timezone.utc)
    audits = {}
    cargowise = {}
    for concept_id in SCENARIOS:
        result = extractor_service.run_audit(concept_id)
        result.executed_at = as_of_ts.isoformat()
        # Offline the PDFs are served from /public/nightmares
        result.document_url = f"/nightmares/{SCENARIOS[concept_id]['filename']}"
        audits[concept_id] = json.loads(result.model_dump_json())
        cargowise[concept_id] = cargowise_exporter.generate_diff_payload(result)

    metrics = {
        "penalty_exposure_avoided": audits["concept_1_customs"]["metrics"]["penalty_exposure_avoided"],
        "carrier_overbilling_caught": audits["concept_2_freight"]["metrics"]["carrier_overbilling_caught"],
        "drawback_unclaimed_unlocked": audits["concept_3_drawback"]["metrics"]["drawback_unclaimed_unlocked"],
    }

    graphs = {gid: json.loads(sanctions_screener.get_ownership_graph(gid).model_dump_json()) for gid in GRAPH_IDS}

    engine = HTSClassifierEngine()
    presets = {pid: json.loads(engine.get_preset(pid).model_dump_json()) for pid in HTS_PRESETS}

    valuation_service = CustomsValuationService()
    valuation = valuation_service.audit_entry_valuation()
    disclosure = valuation_service.generate_prior_disclosure(valuation, as_of=as_of_ts)

    return {
        "generated_from": "backend-engine (scripts/export_frontend_snapshot.py)",
        "as_of_date": FIXTURE_AS_OF.isoformat(),
        "aggregate_metrics": metrics,
        "audits": audits,
        "cargowise": cargowise,
        "sanctions_graphs": graphs,
        "hts_presets": presets,
        "assist_items": [json.loads(a.model_dump_json()) for a in valuation_service.DEFAULT_ASSISTS],
        "valuation_audit": json.loads(valuation.model_dump_json()),
        "prior_disclosure": json.loads(disclosure.model_dump_json()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.check:
        current = open(OUT_PATH, encoding="utf-8").read() if os.path.exists(OUT_PATH) else ""
        if current != text:
            print("STALE: frontend snapshot differs from backend output. Run scripts/export_frontend_snapshot.py")
            return 1
        print("Frontend snapshot matches backend output.")
        return 0
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {os.path.relpath(OUT_PATH, REPO_ROOT)} ({len(text):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

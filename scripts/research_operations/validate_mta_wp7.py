from __future__ import annotations
import json
from pathlib import Path
from ovc.research_operations.mta.readiness_synthesis import validate_fixture, validate_reference
ROOT=Path(__file__).resolve().parents[2]
REFERENCE=ROOT/"docs/releases/market-translation-audit-v0-2/mta-g7/MTA_WP7_READINESS_SYNTHESIS_REFERENCE.json"
FIXTURE=ROOT/"fixtures/research_operations/mta/MTA_WP7_ROUTE_FIXTURES_v0_1.json"
def load(path:Path): return json.loads(path.read_text(encoding="utf-8"))
def main()->int:
 print(json.dumps({"reference":validate_reference(load(REFERENCE)),"fixture":validate_fixture(load(FIXTURE))},sort_keys=True))
 return 0
if __name__=="__main__": raise SystemExit(main())

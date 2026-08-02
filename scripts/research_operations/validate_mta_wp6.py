from __future__ import annotations
import json
from pathlib import Path
from ovc.research_operations.mta.overlap_independence_audit import validate_reference
ROOT=Path(__file__).resolve().parents[2]
def main()->int:
 p=ROOT/'docs/releases/market-translation-audit-v0-2/mta-g6/MTA_WP6_OVERLAP_INDEPENDENCE_AUDIT_REFERENCE.json'
 print(json.dumps(validate_reference(json.loads(p.read_text())),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())

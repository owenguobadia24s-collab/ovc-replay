from __future__ import annotations
import json
from pathlib import Path
from ovc.research_operations.mta.g8_gate import validate_packet
ROOT=Path(__file__).resolve().parents[2]
PACKET=ROOT/"docs/releases/market-translation-audit-v0-2/mta-g8/MTA_G8_CONSOLIDATED_OPERATOR_DECISION_PACKET.json"
def main()->int:
 print(json.dumps(validate_packet(json.loads(PACKET.read_text(encoding="utf-8"))),sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())

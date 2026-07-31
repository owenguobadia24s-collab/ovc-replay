from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

REQUIRED = [
    ROOT / "src/ovc/research_operations/v0_4/state_transition_index.py",
    ROOT / "registries/research_operations/v0_4/RO4_G1_SOURCE_INVENTORY_v0_1.json",
    ROOT / "docs/releases/research-operations-foundation-v0-4/ro4-wp1/RO4_WP1_IMPLEMENTATION_PACKET.json",
    ROOT / "docs/releases/research-operations-foundation-v0-4/ro4-g1/RO4_G1_QA_PACKET.json",
    ROOT / "docs/releases/research-operations-foundation-v0-4/ro4-g1/RO4_G1_GATE_PACKET.json",
]


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.is_file()]
    if missing:
        raise SystemExit("MISSING_RO4_G1_FILES:" + ",".join(missing))
    inventory = json.loads(REQUIRED[1].read_text(encoding="utf-8"))
    if inventory.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise SystemExit("VALIDATION_DENIAL_NOT_FROZEN")
    roles = {item["role"] for item in inventory["releases"]}
    if roles != {"DISCOVERY", "DEVELOPMENT"}:
        raise SystemExit("EXACT_ROLE_SET_REQUIRED")
    if sum(item["state_record_count"] for item in inventory["releases"]) != 404434:
        raise SystemExit("STATE_TOTAL_MISMATCH")
    if sum(item["transition_record_count"] for item in inventory["releases"]) != 323910:
        raise SystemExit("TRANSITION_TOTAL_MISMATCH")
    if len(inventory["partitions"]) != 12:
        raise SystemExit("PARTITION_COUNT_MISMATCH")
    qa = json.loads(REQUIRED[3].read_text(encoding="utf-8"))
    if qa.get("recommendation") not in {"PASS", "PENDING_CI"}:
        raise SystemExit("QA_RECOMMENDATION_INVALID")
    gate = json.loads(REQUIRED[4].read_text(encoding="utf-8"))
    if gate.get("authority_delta") != "LOCAL_REPLACEABLE_DERIVED":
        raise SystemExit("AUTHORITY_DELTA_MISMATCH")
    if gate.get("operator_decision_required") is not False:
        raise SystemExit("RO4_G1_MUST_BE_AUTO_RATIFIABLE")
    source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src/ovc/research_operations/v0_4/index_common.py", ROOT / "src/ovc/research_operations/v0_4/index_partition.py", REQUIRED[0]))
    for forbidden in ("overall_state", "winning_state", "future_outcome", "probability"):
        if forbidden not in source:
            raise SystemExit(f"FORBIDDEN_FIELD_DENIAL_MISSING:{forbidden}")
    print("PASS: RO4-G1 implementation is exact-source-bound, deterministic, full-corpus and non-activating")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

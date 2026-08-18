from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.research_operations.canonical import canonical_json_bytes
from ovc.research_operations.p2cti.bootstrap import build_generation_zero


CENSUS = ROOT / "registries/research_operations/p2cti/P2CTII_BOOTSTRAP_SOURCE_CENSUS_v0_1.json"
RECEIPT = ROOT / "fixtures/research_operations/p2cti/P2CTII_WP3_SOURCE_REPRODUCTION_v0_1.json"
RCCR = ROOT / "registries/implementation/rccr_v0_1/CURRENT_STATE_POINTER.json"
OUTPUT = ROOT / "records/research_operations/p2cti/P2CTII_GENERATION_0_v0_1.json"


def rebuild() -> bytes:
    census = json.loads(CENSUS.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    pointer_bytes = RCCR.read_bytes()
    pointer = json.loads(pointer_bytes)
    import hashlib
    bundle = build_generation_zero(
        census=census, source_reproduction=receipt,
        rccr_pointer_ref=RCCR.relative_to(ROOT).as_posix(),
        rccr_pointer_sha256=hashlib.sha256(pointer_bytes).hexdigest(),
        rccr_semantic_generation=pointer["current_state"], g2_alg_status="PASS",
    )
    return canonical_json_bytes(bundle)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--emit", action="store_true")
    args = parser.parse_args()
    rebuilt = rebuild()
    if args.emit:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(rebuilt)
    if args.check and (not OUTPUT.exists() or OUTPUT.read_bytes() != rebuilt):
        raise SystemExit("Generation-0 canonical rebuild mismatch")
    print(json.loads(rebuilt)["content_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

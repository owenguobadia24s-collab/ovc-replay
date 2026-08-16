from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from ovc.development.skills.vit_assurance_decoupling import (
    build_aa0_reuse_authorization,
    encode_reuse_authorization,
)


def _load(path: str) -> Mapping[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise SystemExit(f"expected JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a canonical AA0 reuse authorization after VIT placement refresh.")
    parser.add_argument("--previous-lineage", required=True)
    parser.add_argument("--current-lineage", required=True)
    parser.add_argument("--head-movement-receipt", required=True)
    args = parser.parse_args()
    record = build_aa0_reuse_authorization(
        previous_lineage=_load(args.previous_lineage),
        current_lineage=_load(args.current_lineage),
        head_movement_receipt=_load(args.head_movement_receipt),
    )
    print(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print(f"VIT-AA0-Reuse-B64: {encode_reuse_authorization(record)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

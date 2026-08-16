from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.research_operations.rccr.core import canonical_json_bytes
from ovc.research_operations.rccr.read_models import query_read_model


def main() -> int:
    parser = argparse.ArgumentParser(description="Query a deterministic RCCR derived read model.")
    parser.add_argument("model", type=Path)
    parser.add_argument("--capability-id")
    parser.add_argument("--item-id")
    args = parser.parse_args()

    if args.capability_id and args.item_id:
        parser.error("choose at most one query selector")
    model = json.loads(args.model.read_text(encoding="utf-8"))
    result = query_read_model(
        model,
        capability_id=args.capability_id,
        item_id=args.item_id,
    )
    print(canonical_json_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

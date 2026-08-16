from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.development.skills.vit_current_state import resolve_current_vit_query


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve current VIT state from current pointers and authority only.")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    result = resolve_current_vit_query(Path(args.repo).resolve())
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

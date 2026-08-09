from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.programme_genesis.topology_diff import build_topology_diff, verify_topology_diff


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an authority-neutral GRT commit-to-commit topology diff from two materialized read models.")
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    diff = build_topology_diff(_read(args.before), _read(args.after))
    verify_topology_diff(diff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(diff, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": diff["schema"],
        "before": diff["before"],
        "after": diff["after"],
        "change_count": diff["change_count"],
        "change_type_counts": diff["change_type_counts"],
        "diff_sha256": diff["diff_sha256"],
        "authority_effect": diff["authority_effect"],
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

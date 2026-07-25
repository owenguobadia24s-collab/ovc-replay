from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.opt_a.release_freeze_gate import freeze_all_roles


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze reviewed OPT-A v2 role workspaces")
    parser.add_argument("--workspaces-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()

    report = freeze_all_roles(
        workspaces_root=args.workspaces_root,
        output_root=args.output_root,
        source_commit=args.source_commit,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

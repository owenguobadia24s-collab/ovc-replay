from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.opt_a.role_workspace import build_all_role_workspaces, build_role_workspace


def main() -> int:
    parser = argparse.ArgumentParser(description="Build governed OPT-A v2 role workspaces from verified WP4 evidence")
    parser.add_argument("--evidence-root", action="append", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--role", choices=["DISCOVERY", "DEVELOPMENT", "VALIDATION", "ALL"], default="ALL")
    parser.add_argument(
        "--unlock-validation-construction",
        action="store_true",
        help="Permit mechanical validation-workspace construction only; does not permit validation consumption.",
    )
    args = parser.parse_args()

    if args.role == "ALL":
        report = build_all_role_workspaces(
            evidence_roots=args.evidence_root,
            output_root=args.output_root,
        )
    else:
        report = build_role_workspace(
            evidence_roots=args.evidence_root,
            output_root=args.output_root,
            role=args.role,
            allow_validation=args.unlock_validation_construction,
        )

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ovc.research_operations.v0_4 import (
    RO4IndexError,
    build_full_sequence_evidence,
    build_sequence_partition,
    finalize_sequence_evidence,
    validate_sequence_evidence,
    workspace_inventory,
)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Build or validate RO4-G3 non-canonical sequence evidence.")
    sub = value.add_subparsers(dest="command", required=True)

    part = sub.add_parser("partition")
    part.add_argument("--index-dir", type=Path, required=True)
    part.add_argument("--workspace", type=Path, required=True)
    part.add_argument("--partition-id", required=True)

    finalize = sub.add_parser("finalize")
    finalize.add_argument("--index-dir", type=Path, required=True)
    finalize.add_argument("--workspace", type=Path, required=True)
    finalize.add_argument("--output-dir", type=Path, required=True)
    finalize.add_argument("--benchmark", type=Path)

    full = sub.add_parser("full")
    full.add_argument("--index-dir", type=Path, required=True)
    full.add_argument("--workspace", type=Path, required=True)
    full.add_argument("--output-dir", type=Path, required=True)
    full.add_argument("--benchmark", type=Path)

    inspect = sub.add_parser("inventory")
    inspect.add_argument("--workspace", type=Path, required=True)

    check = sub.add_parser("validate")
    check.add_argument("--output-dir", type=Path, required=True)
    check.add_argument("--expected-g1-hash", required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "partition":
            result = build_sequence_partition(
                index_dir=args.index_dir,
                workspace_path=args.workspace,
                partition_id=args.partition_id,
            )
        elif args.command == "finalize":
            built = finalize_sequence_evidence(
                index_dir=args.index_dir,
                workspace_path=args.workspace,
                output_dir=args.output_dir,
                benchmark_path=args.benchmark,
            )
            result = {"manifest": built.manifest, "benchmark": built.benchmark}
        elif args.command == "full":
            built = build_full_sequence_evidence(
                index_dir=args.index_dir,
                workspace_path=args.workspace,
                output_dir=args.output_dir,
                benchmark_path=args.benchmark,
            )
            result = {"manifest": built.manifest, "benchmark": built.benchmark}
        elif args.command == "inventory":
            result = workspace_inventory(args.workspace)
        else:
            result = validate_sequence_evidence(args.output_dir, args.expected_g1_hash)
        print(json.dumps(result, sort_keys=True))
    except RO4IndexError as exc:
        print(f"RO4-WP3 blocked: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

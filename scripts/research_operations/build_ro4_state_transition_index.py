from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ovc.research_operations.v0_4 import RO4IndexError, build_full_index, validate_index


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Build or validate the RO4 full-corpus C2 state/transition index.")
    sub = value.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--source-root", type=Path, required=True)
    build.add_argument("--inventory", type=Path, required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument("--benchmark", type=Path, required=True)
    build.add_argument("--partition")
    build.add_argument("--machine", default="LOCAL_REFERENCE_RUNNER")
    build.add_argument("--storage", default="LOCAL_EXTERNAL_ARTIFACT_ROOT")
    check = sub.add_parser("validate")
    check.add_argument("--inventory", type=Path, required=True)
    check.add_argument("--output-dir", type=Path, required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "build":
            result = build_full_index(
                source_root=args.source_root,
                inventory_path=args.inventory,
                output_dir=args.output_dir,
                benchmark_path=args.benchmark,
                selected_partition=args.partition,
                reference_machine=args.machine,
                storage=args.storage,
            )
            print(json.dumps({"manifest": result.manifest, "benchmark": result.benchmark}, sort_keys=True))
        else:
            print(json.dumps(validate_index(args.output_dir, args.inventory), sort_keys=True))
    except RO4IndexError as exc:
        print(f"RO4-WP1 blocked: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ovc.research_operations.v0_4 import RO4IndexError, build_g2_evidence, validate_g2_evidence


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Build or validate RO4-G2 matrix, persistence and conflict evidence.")
    sub = value.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--index-dir", type=Path, required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument("--benchmark", type=Path, required=True)
    build.add_argument("--machine", default="LOCAL_REFERENCE_RUNNER")
    build.add_argument("--storage", default="LOCAL_EXTERNAL_ARTIFACT_ROOT")
    check = sub.add_parser("validate")
    check.add_argument("--output-dir", type=Path, required=True)
    check.add_argument("--expected-g1-hash", required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "build":
            result = build_g2_evidence(
                index_dir=args.index_dir,
                output_dir=args.output_dir,
                benchmark_path=args.benchmark,
                reference_machine=args.machine,
                storage=args.storage,
            )
            print(json.dumps({"manifest": result.manifest, "benchmark": result.benchmark}, sort_keys=True))
        else:
            print(json.dumps(validate_g2_evidence(args.output_dir, args.expected_g1_hash), sort_keys=True))
    except RO4IndexError as exc:
        print(f"RO4-WP2 blocked: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

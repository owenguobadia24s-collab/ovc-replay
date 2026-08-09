#!/usr/bin/env python3
"""Classify OVC main-head movement against a packet dependency footprint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.head_churn import classify_main_head_movement  # noqa: E402


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_paths(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-main", required=True)
    parser.add_argument("--current-main", required=True)
    parser.add_argument("--changed-main-paths-file", type=Path, required=True)
    parser.add_argument("--footprint", type=Path)
    parser.add_argument(
        "--policy",
        type=Path,
        default=ROOT / "registries/development/OVC_PARALLEL_DEVELOPMENT_HEAD_MOVEMENT_POLICY_v0_1.json",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-semantic", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        footprint = _load_json(args.footprint) if args.footprint else None
        policy = _load_json(args.policy)
        receipt = classify_main_head_movement(
            baseline_main_sha=args.baseline_main,
            current_main_sha=args.current_main,
            changed_main_paths=_read_paths(args.changed_main_paths_file),
            footprint=footprint,
            policy=policy,
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCK", "reason": "HEAD_CHURN_CLASSIFIER_INPUT_INVALID", "detail": str(exc)}, sort_keys=True))
        return 2

    encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    if args.fail_on_semantic and receipt["classification"] in {
        "SEMANTIC_AUTHORITY_RELEVANT",
        "UNRESOLVED_REQUIRES_FOOTPRINT",
    }:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

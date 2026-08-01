#!/usr/bin/env python3
"""Select a deterministic OVC test profile from changed repository paths."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.test_selection import (  # noqa: E402
    TestSelectionError,
    load_test_profile_registry,
    select_test_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--changed-path", action="append", default=[])
    parser.add_argument("--changed-paths-file", type=Path)
    parser.add_argument("--stage", choices=["CHANGE", "FINAL_HEAD", "GATE_REPLAY"], default="CHANGE")
    parser.add_argument("--gate-id")
    parser.add_argument("--gate-command")
    parser.add_argument("--output", type=Path, help="Optional compact manifest destination")
    return parser


def _paths(args: argparse.Namespace) -> list[str]:
    result = list(args.changed_path)
    if args.changed_paths_file:
        result.extend(
            line.strip()
            for line in args.changed_paths_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return result


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        registry = load_test_profile_registry(args.registry)
        manifest = select_test_manifest(
            _paths(args),
            registry,
            stage=args.stage,
            gate_id=args.gate_id,
            gate_command=args.gate_command,
        )
        text = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text + "\n", encoding="utf-8", newline="\n")
        print(text)
        return 0 if manifest["status"] == "PASS" else 1
    except (OSError, TestSelectionError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCK", "reason": "TEST_SELECTION_REQUEST_INVALID", "detail": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

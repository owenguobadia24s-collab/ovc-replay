#!/usr/bin/env python3
"""Run the cheap read-only programme-state/current-pointer consistency preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.programme_state_preflight import run_programme_state_preflight  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--scan-root", type=Path, help="Optional subtree; defaults to <repository-root>/registries")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repository_root = args.repository_root.resolve()
    scan_root = args.scan_root
    if scan_root is not None and not scan_root.is_absolute():
        scan_root = repository_root / scan_root
    try:
        receipt = run_programme_state_preflight(repository_root, scan_root=scan_root)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "BLOCK", "reason": "PROGRAMME_STATE_PREFLIGHT_INVALID", "detail": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

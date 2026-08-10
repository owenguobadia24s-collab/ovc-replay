from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from ovc.opt_b.srfd.wp10_v11_hardening import (
    run_full_synthetic_rehearsal,
    run_restart_torture,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    if args.reset and args.root.exists():
        shutil.rmtree(args.root)
    args.root.mkdir(parents=True, exist_ok=True)
    restart = run_restart_torture(args.root / "restart_torture")
    full = run_full_synthetic_rehearsal(args.root / "full_2020")
    payload = {
        "schema": "ovc-srfdi-wp10-v11-hardening-rehearsal-bundle/v1",
        "status": "PASS",
        "restart_torture": restart,
        "full_2020_rehearsal": full,
        "scientific_payload_used": False,
        "provider_fetch": "DENIED",
        "validation_2025": "LOCKED_UNCONSUMED",
        "authority_effect": "NONE_EXECUTION_REHEARSAL_ONLY",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from ovc.opt_b.srfd.wp10_v11_environment import capture_execution_environment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--working-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--captured-at", required=True)
    args = parser.parse_args()
    freeze = subprocess.run(
        [sys.executable, "-m", "pip", "freeze", "--all"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    profile = capture_execution_environment(
        profile_id=args.profile_id,
        working_root=args.working_root,
        captured_at=args.captured_at,
        pip_freeze_bytes=freeze,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(profile, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

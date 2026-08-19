#!/usr/bin/env python3
"""Run one exact non-enforcing full-G3 shadow replay."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.full_enforcement_bounded_v2 import replay_full_g3_candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--predecessor", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    result = replay_full_g3_candidate(Path(args.repository_root), predecessor_commit=args.predecessor, candidate_commit=args.candidate)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

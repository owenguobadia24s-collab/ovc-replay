#!/usr/bin/env python3
"""Fresh-process runner for C2S-SPTOI WP10 integrated assurance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.research_operations.spto.integrated_assurance import (
    build_artifact_reuse_snapshot,
    build_reference_snapshot,
    build_sharded_null_pack,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=("reference", "artifact-reuse", "sharded"), required=True)
    args = parser.parse_args()
    if args.mode == "reference":
        value = build_reference_snapshot()
        result = {"mode": args.mode, "snapshot_id": value["snapshot_id"]}
    elif args.mode == "artifact-reuse":
        value = build_artifact_reuse_snapshot(args.root)
        result = {"mode": args.mode, "snapshot_id": value["snapshot_id"]}
    else:
        value = build_sharded_null_pack(
            (("FG-NC", "FG-NO"), ("FG-NORD", "FG-NCORE"), ("FG-NFO", "FG-NBROAD"))
        )
        result = {"mode": args.mode, "pack_id": value["pack_id"]}
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

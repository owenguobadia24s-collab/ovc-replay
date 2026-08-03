#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ovc.programme_genesis import (
    UpkeepError,
    load_upkeep_registry,
    persist_candidate_event,
    preview_candidate_events,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview bounded Programme Genesis upkeep candidate events.")
    parser.add_argument("--finding-file", required=True, type=Path, help="JSON object or array of explicit source findings")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("registries/governance/programme_genesis/UPKEEP_CANDIDATE_EVENT_REGISTRY_v0_1.json"),
    )
    parser.add_argument("--existing-programme-id", action="append", required=True)
    parser.add_argument("--target-branch", required=True)
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--persist", action="store_true", help="Attempt persistence; denied while registry is disabled")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        raw = json.loads(args.finding_file.read_text(encoding="utf-8"))
        findings = raw if isinstance(raw, list) else [raw]
        if not all(isinstance(item, dict) for item in findings):
            raise UpkeepError("finding file must contain an object or array of objects")
        registry = load_upkeep_registry(args.registry)
        candidates = preview_candidate_events(
            findings,
            registry=registry,
            existing_programme_ids=args.existing_programme_id,
            target_branch=args.target_branch,
        )
        if args.persist:
            paths = [
                str(
                    persist_candidate_event(
                        args.repository_root,
                        candidate,
                        registry=registry,
                        branch_name=args.target_branch,
                        existing_programme_ids=args.existing_programme_id,
                    )
                )
                for candidate in candidates
            ]
            output = {"status": "PERSISTED", "paths": paths, "candidates": candidates}
        else:
            output = {
                "status": "PREVIEW_ONLY_DISABLED_PENDING_PG_G7",
                "authority_effect": "NONE",
                "candidate_count": len(candidates),
                "candidates": candidates,
            }
        json.dump(output, sys.stdout, sort_keys=True, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    except (OSError, json.JSONDecodeError, UpkeepError, KeyError) as exc:
        print(f"PG upkeep preview failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

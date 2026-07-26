from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.opt_b.c2.replay import RELEASE_BINDINGS, ReplayError, run_verified_role_replay, sha256, verify_canonical_release


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _output_inventory(root: Path) -> dict[str, dict[str, int | str]]:
    return {
        path.relative_to(root).as_posix(): {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(root.rglob("*.jsonl"))
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify and replay exact canonical OPT-B.C1 v2 manifest-bound shards for C2 WP5."
    )
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)

    try:
        verified = [
            verify_canonical_release(args.release_root / role.lower(), RELEASE_BINDINGS[role])
            for role in ("DISCOVERY", "DEVELOPMENT")
        ]
    except ReplayError as exc:
        receipt = {"schema": "ovc-opt-b-c2-wp5-canonical-intake/v2", "status": "BLOCKED_CANONICAL_INTAKE", "error": str(exc)}
        _write(args.output_root / "WP5_CANONICAL_INTAKE_RECEIPT.json", receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 2

    intake = {
        "schema": "ovc-opt-b-c2-wp5-canonical-intake/v2",
        "status": "PASS_CANONICAL_MANIFEST_AND_FULL_BYTE_VERIFICATION",
        "releases": [
            {
                "role": item.binding.role,
                "release_id": item.binding.release_id,
                "manifest_id": item.binding.manifest_id,
                "manifest_sha256": item.manifest_sha256,
                "record_shards": len(item.record_paths),
                "manifest_bound_payload_objects": item.payload_object_count,
                "canonical_objects_including_manifest": item.canonical_object_count,
                "payload_bytes": item.payload_bytes,
                "scope_shard_counts": [
                    {"clock": clock, "side": side, "shards": count}
                    for clock, side, count in item.scope_shard_counts
                ],
            }
            for item in verified
        ],
        "totals": {
            "record_shards": sum(len(item.record_paths) for item in verified),
            "manifest_bound_payload_objects": sum(item.payload_object_count for item in verified),
            "canonical_objects_including_manifests": sum(item.canonical_object_count for item in verified),
        },
        "validation_consumption": "LOCKED_UNCONSUMED",
    }
    _write(args.output_root / "WP5_CANONICAL_INTAKE_RECEIPT.json", intake)
    if args.verify_only:
        print(json.dumps(intake, indent=2, sort_keys=True))
        return 0

    try:
        summaries = [run_verified_role_replay(item, args.output_root) for item in verified]
    except ReplayError as exc:
        blocker = {
            "schema": "ovc-opt-b-c2-wp5-replay-blocker/v2",
            "status": "BLOCKED_C1_C2_RECORD_CONTRACT_MISMATCH",
            "canonical_intake": "PASS",
            "error": str(exc),
            "required_resolution": (
                "Realign the C2 handoff and structure engine to the published C1 primitive schema and exact "
                "OPT-A price parents; do not synthesize missing absolute-price, first-valid, level, container, "
                "or combined-scope inputs."
            ),
            "local_candidate_release": "NONE",
            "selector": "NONE",
            "validation_consumption": "LOCKED_UNCONSUMED",
            "probability": "NONE",
            "exposure": "NONE",
            "trading": "NONE",
            "execution": "NONE",
        }
        _write(args.output_root / "WP5_REPLAY_BLOCKER_RECEIPT.json", blocker)
        print(json.dumps(blocker, indent=2, sort_keys=True))
        return 3

    receipt = {
        "schema": "ovc-opt-b-c2-wp5-local-replay/v2",
        "status": "PASS_LOCAL_REPLAY",
        "canonical_intake": intake,
        "roles": [summary.__dict__ for summary in summaries],
        "outputs": _output_inventory(args.output_root),
        "validation_consumption": "LOCKED_UNCONSUMED",
        "probability": "NONE",
        "exposure": "NONE",
        "trading": "NONE",
        "execution": "NONE",
    }
    _write(args.output_root / "WP5_LOCAL_REPLAY_RECEIPT.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

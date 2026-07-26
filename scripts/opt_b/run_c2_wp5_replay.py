from __future__ import annotations

import argparse
import json
from pathlib import Path

from ovc.opt_b.c2.price_parent import (
    OPT_A_RELEASE_BINDINGS,
    PriceParentError,
    verify_opt_a_release,
)
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
    parser.add_argument("--opt-a-release-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)

    try:
        verified_c1 = [
            verify_canonical_release(args.release_root / role.lower(), RELEASE_BINDINGS[role])
            for role in ("DISCOVERY", "DEVELOPMENT")
        ]
        verified_opt_a = [
            verify_opt_a_release(args.opt_a_release_root / role.lower(), OPT_A_RELEASE_BINDINGS[role])
            for role in ("DISCOVERY", "DEVELOPMENT")
        ]
    except (ReplayError, PriceParentError) as exc:
        receipt = {
            "schema": "ovc-opt-b-c2-wp5-exact-parent-intake/v3",
            "status": "BLOCKED_EXACT_PARENT_INTAKE",
            "error": str(exc),
        }
        _write(args.output_root / "WP5_CANONICAL_INTAKE_RECEIPT.json", receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 2

    intake = {
        "schema": "ovc-opt-b-c2-wp5-exact-parent-intake/v3",
        "status": "PASS_C1_AND_OPT_A_CANONICAL_FULL_BYTE_VERIFICATION",
        "c1_releases": [
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
            for item in verified_c1
        ],
        "opt_a_releases": [
            {
                "role": item.binding.role,
                "release_id": item.binding.release_id,
                "manifest_id": item.binding.manifest_id,
                "manifest_sha256": item.manifest_sha256,
                "manifest_bound_payload_objects": item.binding.payload_file_count,
                "payload_bytes": item.binding.payload_bytes,
                "price_files": item.binding.price_file_count,
            }
            for item in verified_opt_a
        ],
        "totals": {
            "c1_record_shards": sum(len(item.record_paths) for item in verified_c1),
            "c1_manifest_bound_payload_objects": sum(item.payload_object_count for item in verified_c1),
            "c1_canonical_objects_including_manifests": sum(item.canonical_object_count for item in verified_c1),
            "opt_a_manifest_bound_payload_objects": sum(item.binding.payload_file_count for item in verified_opt_a),
            "opt_a_price_files": sum(item.binding.price_file_count for item in verified_opt_a),
        },
        "validation_consumption": "LOCKED_UNCONSUMED",
    }
    _write(args.output_root / "WP5_CANONICAL_INTAKE_RECEIPT.json", intake)
    if args.verify_only:
        print(json.dumps(intake, indent=2, sort_keys=True))
        return 0

    try:
        summaries = [
            run_verified_role_replay(c1, opt_a, args.output_root)
            for c1, opt_a in zip(verified_c1, verified_opt_a)
        ]
    except (ReplayError, PriceParentError, ValueError) as exc:
        blocker = {
            "schema": "ovc-opt-b-c2-wp5-replay-blocker/v3",
            "status": "BLOCKED_EXACT_PARENT_JOIN_OR_ENGINE_ERROR",
            "canonical_intake": "PASS_C1_AND_OPT_A",
            "error": str(exc),
            "required_resolution": (
                "Resolve the exact manifest, source-row, lineage, chronology or deterministic engine error. "
                "Do not synthesize, repair, substitute or relabel either parent."
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
        "schema": "ovc-opt-b-c2-wp5-local-replay/v3",
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

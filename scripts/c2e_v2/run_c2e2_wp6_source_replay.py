#!/usr/bin/env python3
"""Run one exact C2E2-WP6 source replay from an extracted materialisation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import resource
import time

from ovc.opt_b.c2e_v2.boundary_pack import freeze_pack
from ovc.opt_b.c2e_v2.source_replay_runtime import (
    load_json,
    load_materialisation,
    run_source_replay,
    write_run,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materialisation-root", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--boundary-pack", type=Path, required=True)
    parser.add_argument("--authority-token", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-build-commit", required=True)
    parser.add_argument("--code-hash", action="append", default=[])
    args = parser.parse_args()

    run_manifest = load_json(args.run_manifest)
    boundary_pack = load_json(args.boundary_pack)
    token = load_json(args.authority_token)

    frozen = freeze_pack(boundary_pack)
    if frozen["boundary_pack_id"] != boundary_pack.get("boundary_pack_id"):
        raise SystemExit("BOUNDARY_PACK_ID_DRIFT")
    if frozen["logical_sha256"] != boundary_pack.get("logical_sha256"):
        raise SystemExit("BOUNDARY_PACK_LOGICAL_HASH_DRIFT")
    if token.get("status") != "AUTHORIZED_UNCONSUMED" or token.get("consumed") is not False:
        raise SystemExit("RUN_AUTH_TOKEN_NOT_AVAILABLE")
    if token.get("operator_command") != "OVC APPROVE C2E2-G6-RUN-AUTH":
        raise SystemExit("RUN_AUTH_OPERATOR_COMMAND_MISMATCH")
    if token.get("run_manifest_logical_sha256") != run_manifest.get("logical_sha256"):
        raise SystemExit("RUN_AUTH_MANIFEST_BINDING_MISMATCH")
    if token.get("boundary_pack_id") != boundary_pack.get("boundary_pack_id"):
        raise SystemExit("RUN_AUTH_BOUNDARY_PACK_BINDING_MISMATCH")
    if run_manifest.get("mode") != "BOUNDED_REAL_SOURCE_SHADOW_REPLAY_ONLY":
        raise SystemExit("RUN_MANIFEST_MODE_INVALID")
    requirements = run_manifest.get("execution_requirements", {})
    if requirements.get("no_sampling_or_top_k_substitution") is not True:
        raise SystemExit("SAMPLING_DENIAL_NOT_FROZEN")
    if requirements.get("provider_intake") != "NONE" or requirements.get("validation_consumption") != "NONE":
        raise SystemExit("FORBIDDEN_RUN_INPUT_AUTHORITY")

    source = run_manifest["source_materialisation"]
    population = run_manifest["source_population"]
    started = time.perf_counter()
    materialisation = load_materialisation(
        args.materialisation_root,
        expected_manifest_sha=source["manifest_logical_sha256"],
        expected_target_sha=source["target_bundles_sha256"],
        expected_population_sha=population["logical_population_sha256"],
    )
    loaded = time.perf_counter()
    result = run_source_replay(
        materialisation,
        boundary_pack,
        source_build_commit=args.source_build_commit,
    )
    replayed = time.perf_counter()
    source_binding = {
        "materialisation_id": materialisation["manifest"]["materialisation_id"],
        "materialisation_logical_sha256": materialisation["manifest"]["logical_sha256"],
        "target_population_sha256": population["logical_population_sha256"],
    }
    receipt = write_run(
        result,
        args.output_dir,
        source_binding=source_binding,
        boundary_pack_id=boundary_pack["boundary_pack_id"],
        code_hashes=args.code_hash,
    )
    finished = time.perf_counter()
    telemetry = {
        "schema": "c2e_wp6_runtime_telemetry/v0_1",
        "load_seconds": round(loaded - started, 6),
        "replay_seconds": round(replayed - loaded, 6),
        "write_seconds": round(finished - replayed, 6),
        "total_seconds": round(finished - started, 6),
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "frame_count": receipt["frame_count"],
        "stream_record_count": receipt["stream_record_count"],
        "logical_output_sha256": receipt["logical_output_sha256"],
        "sampling": "NONE",
        "provider_intake": "NONE",
        "validation_consumption": "NONE",
    }
    (args.output_dir / "c2e-wp6-runtime-telemetry.json").write_text(
        json.dumps(telemetry, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"receipt": receipt, "telemetry": telemetry}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

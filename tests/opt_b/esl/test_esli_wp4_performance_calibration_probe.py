from __future__ import annotations

import json
import statistics
from pathlib import Path

from ovc.opt_b.esl.c3_reference import measure_reference_vertical_path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "fixtures/opt_b/esl/wp3/bootstrap_c2_input.json"
BUDGET = ROOT / "registries/opt_b/esl/BootstrapPerformanceBudget_v1.json"
PROTOCOL = ROOT / "docs/releases/optb-esl-conformance-v0-1/esli-wp4/ESLI_WP4_CALIBRATION_PROTOCOL.json"


def test_wp4_reference_performance_calibration_probe():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    budget = json.loads(BUDGET.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    batches = []
    for _ in range(protocol["batch_count"]):
        measurement = measure_reference_vertical_path(
            source["c2_observation"], source["profile_outputs"],
            source_generation_id=source["source_generation_id"],
            repetitions=protocol["repetitions_per_batch"],
            warmup=20,
        )
        assert measurement["stable_identities"] == budget["stable_identities"]
        batches.append(measurement)

    hard_fields = protocol["environment_comparability"]["hard_fields"]
    hard_envs = [
        {key: batch["environment"].get(key) for key in hard_fields}
        for batch in batches
    ]
    assert all(env == hard_envs[0] for env in hard_envs), "ESL_CALIBRATION_HARD_ENVIRONMENT_DRIFT"

    envelope = {
        "schema": "ovc-esl-bootstrap-performance-final-calibration/v2",
        "authority": "MEASUREMENT_ONLY_NO_SLO_UNTIL_G4_FINAL_FREEZE",
        "hard_environment": hard_envs[0],
        "observed_image_versions": sorted({batch["environment"].get("image_version") for batch in batches}),
        "batch_count": len(batches),
        "repetitions_per_batch": protocol["repetitions_per_batch"],
        "warmup_per_batch": 20,
        "stable_identities": budget["stable_identities"],
        "paths": {},
        "batches": [
            {
                "environment": batch["environment"],
                "occurrence_assembly": batch["occurrence_assembly"],
                "c3_reference_compile_render": batch["c3_reference_compile_render"],
                "total_vertical_path": batch["total_vertical_path"],
            }
            for batch in batches
        ],
    }
    for path_name in ("occurrence_assembly", "c3_reference_compile_render", "total_vertical_path"):
        envelope["paths"][path_name] = {
            "median_batch_p50_ms": statistics.median(batch[path_name]["p50_ms"] for batch in batches),
            "max_batch_p95_ms": max(batch[path_name]["p95_ms"] for batch in batches),
            "measured_ceiling_ms": max(batch[path_name]["max_ms"] for batch in batches),
            "min_observed_ms": min(batch[path_name]["min_ms"] for batch in batches),
        }
    raise AssertionError(
        "ESLI_WP4_FINAL_CALIBRATION_BATCH="
        + json.dumps(envelope, sort_keys=True, separators=(",", ":"))
    )

from __future__ import annotations

import json
import os
from pathlib import Path

from ovc.opt_b.esl.c3_reference import measure_reference_vertical_path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "fixtures/opt_b/esl/wp3/bootstrap_c2_input.json"
BUDGET = ROOT / "registries/opt_b/esl/BootstrapPerformanceBudget_v1.json"


def test_wp4_reference_performance_calibration_probe():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    budget = json.loads(BUDGET.read_text(encoding="utf-8"))
    measurement = measure_reference_vertical_path(
        source["c2_observation"],
        source["profile_outputs"],
        source_generation_id=source["source_generation_id"],
        repetitions=200,
        warmup=20,
    )
    assert measurement["stable_identities"] == budget["stable_identities"]
    assert budget["authority"] == "IMPLEMENTATION_REGRESSION_ONLY_NO_PRODUCTION_OR_SCIENTIFIC_SLO"

    hard_fields = budget["comparison_policy"]["hard_environment_fields"]
    expected_hard = budget["calibration"]["hard_environment"]
    actual_hard = {key: measurement["environment"].get(key) for key in hard_fields}
    if os.environ.get("GITHUB_ACTIONS") == "true":
        assert actual_hard == expected_hard, (
            "ESL_BOOTSTRAP_PERFORMANCE_HARD_ENVIRONMENT_MISMATCH_VERSIONED_SUPERSESSION_REQUIRED:"
            + json.dumps({"actual": actual_hard, "expected": expected_hard}, sort_keys=True)
        )
    elif actual_hard != expected_hard:
        return

    for path_name, path_budget in budget["paths"].items():
        assert measurement[path_name]["p95_ms"] <= path_budget["measured_ceiling_ms"], (
            f"ESL_BOOTSTRAP_PERFORMANCE_REGRESSION:{path_name}:"
            f"p95={measurement[path_name]['p95_ms']}:"
            f"budget={path_budget['measured_ceiling_ms']}"
        )

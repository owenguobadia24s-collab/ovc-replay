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
        repetitions=budget["calibration"]["protocol"]["repetitions"],
        warmup=budget["calibration"]["protocol"]["warmup"],
    )
    assert measurement["stable_identities"] == budget["stable_identities"]
    assert budget["authority"] == "IMPLEMENTATION_REGRESSION_ONLY_NO_PRODUCTION_OR_SCIENTIFIC_SLO"

    expected_env = budget["calibration"]["environment"]
    actual_env = measurement["environment"]
    if os.environ.get("GITHUB_ACTIONS") == "true":
        assert actual_env == expected_env, (
            "ESL_BOOTSTRAP_PERFORMANCE_ENVIRONMENT_MISMATCH_VERSIONED_SUPERSESSION_REQUIRED:"
            + json.dumps({"actual": actual_env, "expected": expected_env}, sort_keys=True)
        )
    elif actual_env != expected_env:
        # Local/non-CI timing is non-comparable to the pinned hosted-CI budget.
        return

    for path_name, path_budget in budget["paths"].items():
        assert measurement[path_name]["p95_ms"] <= path_budget["max_p95_ms"], (
            f"ESL_BOOTSTRAP_PERFORMANCE_REGRESSION:{path_name}:"
            f"p95={measurement[path_name]['p95_ms']}:"
            f"budget={path_budget['max_p95_ms']}"
        )

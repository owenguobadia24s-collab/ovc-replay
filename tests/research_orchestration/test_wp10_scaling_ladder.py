from __future__ import annotations

from pathlib import Path

from ovc.research_orchestration.benchmark import (
    ALLOWED_SHAPES,
    characterize_ladder,
    classify_shape,
    default_scaling_ladder,
    run_scaling_case,
    run_scaling_ladder,
)
from ovc.research_orchestration.telemetry import validate_metric_coverage

ROOT = Path(__file__).resolve().parents[2]
LADDER = ROOT / "fixtures/research_orchestration/scaling_ladder_v0_1.yaml"


def test_scaling_ladder_fixture_declares_micro_plus_three_increasing_n_values() -> None:
    text = LADDER.read_text(encoding="utf-8")
    assert "scientific_pack_policy: IDENTICAL_ACROSS_LADDER" in text
    for case_id, n in (("MICRO", 8), ("SMALL", 16), ("MEDIUM", 32), ("LARGE_FIXTURE", 64)):
        assert f"case_id: {case_id}" in text
        assert f"n: {n}" in text
    cases = default_scaling_ladder()
    assert len(cases) == 4
    assert [case.n for case in cases] == sorted(case.n for case in cases)
    assert len({case.scientific_pack_id for case in cases}) == 1


def test_multi_n_runtime_characterization_produces_required_operational_evidence() -> None:
    observations = run_scaling_ladder()
    assert len(observations) == 4
    for observation in observations:
        assert observation.pair_count == observation.n * (observation.n - 1) // 2
        assert observation.no_cache_work_units == observation.pair_count
        assert observation.cache_work_units == 0
        assert observation.cache_work_units_avoided == observation.pair_count
        assert observation.artifact_bytes > 0
        assert observation.checkpoint_bytes > 0
        assert observation.checkpoint_overhead_seconds >= 0
        assert observation.restart_recovery_seconds >= 0
        assert observation.wall_seconds >= 0
        assert observation.cpu_seconds >= 0
        validate_metric_coverage(observation.telemetry)
        metrics = observation.telemetry.metric_by_id()
        assert metrics["peak_rss_bytes"].availability == "UNAVAILABLE"
        assert metrics["pair_count"].value == observation.pair_count
        assert observation.telemetry.scientific_effect == "NONE"


def test_pair_work_shape_is_known_quadratic_without_claiming_production_sla() -> None:
    observations = run_scaling_ladder()
    assert classify_shape(observations, metric="pair_count") == "KNOWN_QUADRATIC_WORK_COUNT"
    characterization = characterize_ladder(observations)
    assert characterization["shape"]["pair_count"] == "KNOWN_QUADRATIC_WORK_COUNT"
    assert characterization["shape"]["wall_seconds"] in ALLOWED_SHAPES
    assert characterization["shape"]["cpu_seconds"] in ALLOWED_SHAPES
    assert characterization["scientific_effect"] == "NONE"
    assert "production_sla" not in characterization


def test_cache_and_no_cache_paths_have_identical_scientific_identity() -> None:
    case = default_scaling_ladder()[1]
    first = run_scaling_case(case)
    second = run_scaling_case(case)
    assert first.scientific_hash == second.scientific_hash
    assert first.deterministic_dict() == second.deterministic_dict()


def test_predicted_exact_pair_work_and_observed_telemetry_are_kept_separate() -> None:
    observation = run_scaling_case(default_scaling_ladder()[0])
    metrics = observation.telemetry.metric_by_id()
    predicted_pair_work = observation.n * (observation.n - 1) // 2
    assert predicted_pair_work == observation.no_cache_work_units
    assert metrics["wall_seconds"].availability == "AVAILABLE"
    assert metrics["cpu_seconds"].availability == "AVAILABLE"
    assert metrics["core_seconds"].availability == "AVAILABLE"
    assert metrics["worker_count"].value == 1
    assert "PARALLELISM_EFFICIENCY_NOT_MEASURED_SINGLE_WORKER" in observation.telemetry.warnings

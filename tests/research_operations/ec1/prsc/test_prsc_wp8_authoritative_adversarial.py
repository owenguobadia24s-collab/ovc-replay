from __future__ import annotations

import json
from pathlib import Path

from ovc.research_operations.prsc.adversarial import build_wp1_wp7_adversarial_handlers
from ovc.research_operations.prsc.capacity import (
    MEASUREMENT_SOURCE,
    PEAK_MEMORY_QUANTITY,
    measure_synthetic_capacity_tiers,
)
from ovc.research_operations.prsc.wp8_runner import (
    EXPECTED_AV_FIXTURES,
    execute_registered_fixtures,
    execute_wp8_assurance,
)


ROOT = Path(__file__).resolve().parents[4]
DETERMINISTIC_CAPACITY_KEYS = (
    "tier_id",
    "candidate_count",
    "surrogate_count",
    "representation_count",
    "time_partition_count",
    "context_partition_count",
    "boundary_count",
    "artifact_bytes",
    "review_units",
    "work_units",
    "component_bytes",
)


def _fixture() -> dict:
    return json.loads(
        (
            ROOT
            / "fixtures/research_operations/ec1/prsc/prsc_wp8_assurance_fixture_v0_1.json"
        ).read_text(encoding="utf-8")
    )


def _deterministic_capacity_projection(row: dict) -> dict:
    return {key: row[key] for key in DETERMINISTIC_CAPACITY_KEYS}


def test_authoritative_av_prsc_01_to_15_execute_against_wp1_wp7_surfaces():
    results = execute_registered_fixtures(build_wp1_wp7_adversarial_handlers())
    assert [row["fixture_id"] for row in results] == list(EXPECTED_AV_FIXTURES)
    assert all(row["status"] == "PASS" for row in results)
    by_id = {row["fixture_id"]: row for row in results}
    assert by_id["AV-PRSC-01"]["observed"]["owner_component_count"] == 2
    assert by_id["AV-PRSC-02"]["observed"]["no_edge_semantics"] == "INDEPENDENCE_UNKNOWN"
    assert by_id["AV-PRSC-07"]["observed"]["owner_label_read_attempt_blocked"] is True
    assert by_id["AV-PRSC-09"]["observed"]["redefinition_blocked"] is True
    assert by_id["AV-PRSC-10"]["observed"]["review_status"] == "REVIEW_CAPACITY_EXCEEDED"
    assert by_id["AV-PRSC-11"]["observed"]["rollback_blocked"] is True
    assert by_id["AV-PRSC-12"]["observed"]["disposition"] == "REJECT_CURRENT_CLAIM"
    assert by_id["AV-PRSC-13"]["observed"]["confirmatory_status"] == "DENIED"
    assert by_id["AV-PRSC-14"]["observed"]["authority_resolution"] == "BLOCK"
    assert by_id["AV-PRSC-15"]["observed"]["optimized_path"] == "QUARANTINED"


def test_bounded_synthetic_tiers_materialise_actual_peak_rss_measurements():
    measurements, evidence = measure_synthetic_capacity_tiers(_fixture()["synthetic_tiers"])
    assert [row.tier_id for row in measurements] == ["TINY", "SMALL", "MEDIUM"]
    assert [row.artifact_bytes for row in measurements] == [2989, 44069, 713349]
    assert all(row.peak_memory_bytes > 0 for row in measurements)
    assert all(row.peak_memory_bytes % 1024 == 0 for row in measurements)
    assert [row.review_units for row in measurements] == [64, 704, 9472]
    assert [row["work_units"] for row in evidence] == [248, 3744, 58496]
    assert all(row["measurement_source"] == MEASUREMENT_SOURCE for row in evidence)
    assert all(row["peak_memory_measurement"]["peak_memory_quantity"] == PEAK_MEMORY_QUANTITY for row in evidence)
    assert all(row["peak_memory_measurement"]["isolated_fresh_process"] is True for row in evidence)
    assert all(row["peak_memory_measurement"]["os_rss"] is True for row in evidence)
    assert all(row["peak_memory_measurement"]["platform_system"] == "Linux" for row in evidence)
    assert all(row["scientific_effect"] == "NONE" for row in evidence)
    print(
        "PRSC_WP8_CAPACITY_RUNTIME_EVIDENCE="
        + json.dumps(list(evidence), sort_keys=True, separators=(",", ":"))
    )


def test_final_wp8_candidate_bundle_freezes_budgets_without_scope_reduction():
    measurements, _ = measure_synthetic_capacity_tiers(_fixture()["synthetic_tiers"])
    bundle = execute_wp8_assurance(
        bundle_id="PRSCI-WP8-MECHANICAL-CONFORMANCE-CANDIDATE-v0.1",
        fixture_handlers=build_wp1_wp7_adversarial_handlers(),
        equivalence_families={},
        measurements=measurements,
        protected_source_survivors=0,
    )
    assert bundle["status"] == "PASS_CANDIDATE"
    assert bundle["protected_source_reachability"] == "ZERO_SURVIVORS"
    assert bundle["equivalence_results"] == []
    assert bundle["operational_budget"]["limits"]["candidate_count"] == 160
    assert bundle["operational_budget"]["limits"]["surrogate_count"] == 320
    assert bundle["operational_budget"]["limits"]["artifact_bytes"] == 891686
    assert bundle["operational_budget"]["limits"]["peak_memory_bytes"] == int(
        max(row.peak_memory_bytes for row in measurements) * 1.25
    )
    assert bundle["operational_budget"]["limits"]["review_units"] == 11840
    assert bundle["operational_budget"]["scope_reduction_permitted"] is False
    assert bundle["operational_budget"]["sampling_permitted"] is False
    assert bundle["review_budget"]["review_limits"] == {
        "review_units": 11840,
        "candidate_count": 160,
    }
    assert bundle["review_budget"]["top_n_permitted"] is False
    assert bundle["review_budget"]["deterministic_batching_required"] is True


def test_materialised_wp8_evidence_is_pinned_actual_rss_and_current_run_fits_budget():
    fixture = _fixture()
    measurements, evidence = measure_synthetic_capacity_tiers(fixture["synthetic_tiers"])
    generated_bundle = execute_wp8_assurance(
        bundle_id="PRSCI-WP8-MECHANICAL-CONFORMANCE-CANDIDATE-v0.1",
        fixture_handlers=build_wp1_wp7_adversarial_handlers(),
        equivalence_families={},
        measurements=measurements,
        protected_source_survivors=0,
    )
    evidence_root = ROOT / "docs/programmes/ec1-prsc-v0-1/wp8"
    materialised_bundle = json.loads(
        (evidence_root / "PRSCI_WP8_MECHANICAL_CONFORMANCE_BUNDLE_v0_1.json").read_text(encoding="utf-8")
    )
    materialised_capacity = json.loads(
        (evidence_root / "PRSCI_WP8_CAPACITY_EVIDENCE_v0_1.json").read_text(encoding="utf-8")
    )
    materialised_av = json.loads(
        (evidence_root / "PRSCI_WP8_ADVERSARIAL_RESULTS_v0_1.json").read_text(encoding="utf-8")
    )
    materialised_operational = json.loads(
        (evidence_root / "PRSCI_WP8_OPERATIONAL_BUDGET_v0_1.json").read_text(encoding="utf-8")
    )
    materialised_review = json.loads(
        (evidence_root / "PRSCI_WP8_REVIEW_BUDGET_v0_1.json").read_text(encoding="utf-8")
    )

    assert materialised_capacity["measurement_method"] == MEASUREMENT_SOURCE
    assert materialised_capacity["peak_memory_quantity"] == PEAK_MEMORY_QUANTITY
    assert materialised_capacity["environment_binding"]["python_version"].startswith("3.11.")
    assert materialised_capacity["environment_binding"]["platform_system"] == "Linux"
    assert materialised_capacity["environment_binding"]["source_workflow_run_id"]
    assert materialised_capacity["environment_binding"]["source_commit"]
    assert len(materialised_capacity["tiers"]) == len(evidence)
    for materialised, current in zip(materialised_capacity["tiers"], evidence):
        assert _deterministic_capacity_projection(materialised) == _deterministic_capacity_projection(current)
        assert materialised["measurement_source"] == MEASUREMENT_SOURCE
        assert materialised["peak_memory_bytes"] > 0
        assert materialised["peak_memory_measurement"]["peak_memory_quantity"] == PEAK_MEMORY_QUANTITY
        assert materialised["peak_memory_measurement"]["os_rss"] is True
        assert materialised["peak_memory_measurement"]["isolated_fresh_process"] is True

    expected_peak_budget = int(
        max(row["peak_memory_bytes"] for row in materialised_capacity["tiers"]) * 1.25
    )
    assert materialised_operational["limits"] == {
        "candidate_count": 160,
        "surrogate_count": 320,
        "artifact_bytes": 891686,
        "peak_memory_bytes": expected_peak_budget,
        "review_units": 11840,
    }
    assert all(
        measurement.peak_memory_bytes <= materialised_operational["limits"]["peak_memory_bytes"]
        for measurement in measurements
    )
    assert materialised_operational["scope_reduction_permitted"] is False
    assert materialised_operational["sampling_permitted"] is False
    assert materialised_review == generated_bundle["review_budget"]

    materialised_capacity_by_tier = {
        row["tier_id"]: row for row in materialised_capacity["tiers"]
    }
    for row in materialised_bundle["capacity_results"]:
        source = materialised_capacity_by_tier[row["tier_id"]]
        assert row["peak_memory_bytes"] == source["peak_memory_bytes"]
        assert row["artifact_bytes"] == source["artifact_bytes"]
        assert row["review_units"] == source["review_units"]
        assert row["status"] == "PASS"
    assert materialised_bundle["operational_budget"] == materialised_operational
    assert materialised_bundle["review_budget"] == materialised_review
    assert materialised_bundle["status"] == "PASS_CANDIDATE"
    assert materialised_bundle["protected_source_reachability"] == "ZERO_SURVIVORS"
    assert materialised_av["results"] == generated_bundle["fixture_results"]
    assert materialised_av["all_registered_fixtures_executed"] is True
    assert materialised_av["all_status_pass"] is True
    assert materialised_capacity["scientific_effect"] == "NONE"
    assert materialised_capacity["authority_effect"] == "NONE"

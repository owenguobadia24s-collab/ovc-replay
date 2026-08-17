from __future__ import annotations

import json
from pathlib import Path

from ovc.research_operations.prsc.adversarial import build_wp1_wp7_adversarial_handlers
from ovc.research_operations.prsc.capacity import measure_synthetic_capacity_tiers
from ovc.research_operations.prsc.wp8_runner import (
    EXPECTED_AV_FIXTURES,
    execute_registered_fixtures,
    execute_wp8_assurance,
)


ROOT = Path(__file__).resolve().parents[4]


def _fixture() -> dict:
    return json.loads(
        (
            ROOT
            / "fixtures/research_operations/ec1/prsc/prsc_wp8_assurance_fixture_v0_1.json"
        ).read_text(encoding="utf-8")
    )


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


def test_bounded_synthetic_tiers_materialise_deterministic_non_scientific_measurements():
    measurements, evidence = measure_synthetic_capacity_tiers(_fixture()["synthetic_tiers"])
    assert [row.tier_id for row in measurements] == ["TINY", "SMALL", "MEDIUM"]
    assert [row.artifact_bytes for row in measurements] == [2989, 44069, 713349]
    assert [row.peak_memory_bytes for row in measurements] == [1585, 26305, 444673]
    assert [row.review_units for row in measurements] == [64, 704, 9472]
    assert [row["work_units"] for row in evidence] == [248, 3744, 58496]
    assert all(row["measurement_source"] == "CANONICAL_LOGICAL_SYNTHETIC_WORKLOAD_BYTES" for row in evidence)
    assert all(row["scientific_effect"] == "NONE" for row in evidence)


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
    assert bundle["operational_budget"]["limits"] == {
        "candidate_count": 160,
        "surrogate_count": 320,
        "artifact_bytes": 891686,
        "peak_memory_bytes": 555841,
        "review_units": 11840,
    }
    assert bundle["operational_budget"]["scope_reduction_permitted"] is False
    assert bundle["operational_budget"]["sampling_permitted"] is False
    assert bundle["review_budget"]["review_limits"] == {
        "review_units": 11840,
        "candidate_count": 160,
    }
    assert bundle["review_budget"]["top_n_permitted"] is False
    assert bundle["review_budget"]["deterministic_batching_required"] is True


def test_materialised_wp8_evidence_reproduces_exact_candidate_outputs():
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
    assert materialised_bundle == generated_bundle
    assert materialised_operational == generated_bundle["operational_budget"]
    assert materialised_review == generated_bundle["review_budget"]
    assert materialised_av["results"] == generated_bundle["fixture_results"]
    assert materialised_av["all_registered_fixtures_executed"] is True
    assert materialised_av["all_status_pass"] is True
    comparable_capacity = []
    for row in evidence:
        comparable_capacity.append({
            key: value for key, value in row.items()
            if key not in {"scientific_effect", "authority_effect"}
        })
    assert materialised_capacity["tiers"] == comparable_capacity
    assert materialised_capacity["scientific_effect"] == "NONE"
    assert materialised_capacity["authority_effect"] == "NONE"

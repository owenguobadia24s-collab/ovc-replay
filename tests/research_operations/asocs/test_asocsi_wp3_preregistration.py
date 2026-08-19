from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ovc.research_operations.asocs.instrumentation import (
    logical_scientific_hash,
    observe_record,
    prove_chain_equivalence,
)

ROOT = Path(__file__).resolve().parents[3]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_instrumentation_off_on_preserves_scientific_hashes_and_fvt() -> None:
    fixture = _json(
        "fixtures/research_operations/asocs/wp3/"
        "instrumentation_equivalence_chain_v0_1.json"
    )
    result = prove_chain_equivalence(fixture["records"])
    assert result["result"] == "PASS"
    assert result["layers"] == ["C1", "C2", "C2E"]
    assert result["scientific_hash_differences"] == 0
    assert result["first_valid_identity_differences"] == 0
    assert result["record_mutations"] == 0


def test_instrumentation_is_detached_and_does_not_mutate_owner_record() -> None:
    record = _json(
        "fixtures/research_operations/asocs/wp3/"
        "instrumentation_equivalence_chain_v0_1.json"
    )["records"][0]
    before = json.dumps(record, sort_keys=True, separators=(",", ":"))
    output, observation = observe_record(record, enabled=True)
    after = json.dumps(record, sort_keys=True, separators=(",", ":"))
    assert before == after
    assert output == record
    assert observation is not None
    assert observation.logical_scientific_hash == logical_scientific_hash(record)


def test_g2_threshold_registry_is_complete_and_exact() -> None:
    registry = _json(
        "registries/research_operations/asocs/ASOCSI_G2_THRESHOLD_REGISTRY_v0_1.json"
    )
    adequate = registry["support_rules"]["ADEQUATE_SUPPORT"]
    assert adequate == {
        "minimum_evaluable_cases": 30,
        "minimum_hidden_repeat_exact_or_adjacent_agreement": 0.8,
        "minimum_independent_24h_source_blocks": 10,
        "minimum_target_months": 4,
        "maximum_source_limited_fraction": 0.2,
    }
    bounded = registry["support_rules"]["BOUNDED_SUPPORT"]
    assert bounded["minimum_evaluable_cases"] == 15
    assert bounded["minimum_independent_24h_source_blocks"] == 6
    assert registry["support_rules"]["LOW_SUPPORT"]["evaluable_cases_min"] == 5
    assert registry["support_rules"]["LOW_SUPPORT"]["evaluable_cases_max"] == 14
    assert registry["support_rules"]["INSUFFICIENT_SUPPORT"][
        "evaluable_cases_below"
    ] == 5
    assert registry["secondary_diagnostic_expansion"][
        "maximum_cases_per_construct"
    ] == 60
    assert registry["strong_systematic_falsification"][
        "minimum_material_or_severe_failure_fraction"
    ] == 0.4
    assert registry["critical_single_case_falsifier"]["count"] == 1


def test_sampling_nonce_is_frozen_before_census_and_hashes_exactly() -> None:
    freeze = _json(
        "docs/programmes/asocs-v0-1/implementation/wp3/"
        "ASOCSI_G2_SAMPLING_NONCE_FREEZE_v0_1.json"
    )
    assert freeze["generated_before_s3_census_inspection"] is True
    assert freeze["reviewer_surface_exposure"] is False
    assert freeze["stratum_labels_exposed_to_reviewer"] is False
    assert hashlib.sha256(bytes.fromhex(freeze["nonce_hex"])).hexdigest() == freeze[
        "nonce_sha256"
    ]


def test_runtime_freeze_pins_current_c1_nine_c2_c2e_and_context_identities() -> None:
    freeze = _json(
        "docs/programmes/asocs-v0-1/implementation/wp3/"
        "ASOCSI_G2_RUNTIME_IDENTITY_FREEZE_v0_1.json"
    )
    c2 = _json("registries/opt_b/c2/vnext/C2_VNEXT_ACTIVE_RUNTIME_AUTHORITY_v0_1.json")
    c2e = _json("registries/authority/C2E_ACTIVE_ENGINE_AUTHORITY_v0_1.json")
    context = _json(
        "registries/implementation/occurrence_context/"
        "OCCURRENCE_CONTEXT_ACTIVE_FOUNDATION_AUTHORITY_v0_1.json"
    )
    c1_text = (ROOT / "registries/opt_b/c1/C1_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
    assert "selector_set_id: SELECTOR.OPT-B.C1.ROLESET.v0.2" in c1_text
    assert freeze["c1"]["selector_set_id"] == c2["upstream_requirement"]["selector_set"]
    assert freeze["c2"]["authority_id"] == c2["authority_id"]
    assert freeze["c2"]["active_component_count"] == 9
    assert {x["component"] for x in freeze["c2"]["active_components"]} == set(
        c2["active_components"]
    )
    assert freeze["c2e"]["authority_id"] == c2e["authority_id"]
    assert freeze["c2e"]["active_boundary_pack_logical_sha256"] == c2e[
        "active_boundary_pack_logical_sha256"
    ]
    assert freeze["occurrence_context"]["authority_id"] == context["authority_id"]
    assert freeze["freeze_effect"].endswith(
        "NO_SELECTOR_PACK_SEMANTIC_OR_AUTHORITY_CHANGE"
    )


def test_capacity_and_statistics_freeze_fail_closed_without_semantic_simplification() -> None:
    budget = _json(
        "registries/research_operations/asocs/ASOCSI_G2_CAPACITY_BUDGET_v0_1.json"
    )
    methods = _json(
        "registries/research_operations/asocs/"
        "ASOCSI_G2_STATISTICAL_METHOD_FREEZE_v0_1.json"
    )
    assert budget["hard_ceilings"]["external_output_gib"] == 64
    assert budget["hard_ceilings"]["peak_rss_gib"] == 24
    assert budget["hard_ceilings"]["clean_run_hours"] == 8
    assert budget["on_exceed"] == "CAPACITY_BLOCKED"
    assert "SEMANTIC_SIMPLIFICATION" in budget["forbidden_responses"]
    assert "DAY_SOURCE_BLOCK_CLUSTER_AWARE_RESAMPLING" in methods["primary"]
    assert methods["sensitivity_only"] == ["EPISODE_CLUSTERING"]
    assert "NAIVE_OBSERVATION_BOOTSTRAP" in methods["forbidden"]


def test_g2_preregistration_is_frozen_before_census_and_preserves_authority() -> None:
    freeze = _json(
        "docs/programmes/asocs-v0-1/implementation/wp3/"
        "ASOCSI_G2_PREREGISTRATION_FREEZE_v0_1.json"
    )
    state = _json(
        "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_5_WP3.json"
    )
    pointer = _json(
        "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json"
    )
    current_state = _json(pointer["current_state"])
    assert freeze["frozen_before_s3_census_inspection"] is True
    assert freeze["census_inspection_started"] is False
    assert freeze["review_sampling_started"] is False
    assert freeze["authority_class"] == "ASOCS_AUDIT_ONLY"
    assert freeze["claim_class"] == "ASOCS_SINGLE_STREAM_MORPHOLOGY_COHERENCE"
    assert state["status"] == "COMPLETED"
    assert state["structural_computation_started"] is False
    assert state["next_packet"] == "ASOCSI-WP4"
    assert pointer["programme_id"] == "OVC-ASOCS-6M-v0.1"
    assert pointer["packet_id"] == current_state["packet_id"]
    assert pointer["status"] == current_state["status"]
    assert pointer["next_packet"] == current_state["next_packet"]
    assert "VALIDATION_CONSUMPTION" in freeze["retained_denials"]


def test_g2_decision_and_qa_are_non_reserved_pass() -> None:
    decision = _json(
        "docs/programmes/asocs-v0-1/implementation/wp3/"
        "ASOCSI_G2_DELEGATED_DECISION_v0_1.json"
    )
    qa = _json(
        "docs/programmes/asocs-v0-1/implementation/wp3/"
        "ASOCSI_WP3_QA_PACKET_v0_1.json"
    )
    assert decision["decision"] == "PASS_DELEGATED"
    assert decision["authority_delta"] == "NONE"
    assert decision["next_packet"] == "ASOCSI-WP4"
    assert qa["qa_recommendation"] == "PASS"
    assert qa["blocking_findings"] == []
    assert qa["authority_delta"] == "NONE"

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.cbs.assurance import (
    AV_DISPOSITIONS, adjudicate_fixture, classify_amendment, validate_independent_review,
    validate_temporal_diversity,
)
from ovc.research_operations.cbs.capacity import build_capacity_receipt
from ovc.research_operations.cbs.comparators.common import build_estimate
from ovc.research_operations.cbs.controls import (
    REQUIRED_CONTROL_CLASSES, assess_null_adequacy, build_null_execution_manifest, validate_control_coverage,
)
from ovc.research_operations.cbs.evidence import (
    build_concordance_surface, build_evidence_dossier, build_method_disagreement_record, build_uncertainty_record,
)
from ovc.research_operations.cbs.identity import CBSContractError
from ovc.research_operations.cbs.replay import build_replay_receipt
from ovc.research_operations.cbs.vectors import SUPPORT_PLANES, build_boundary_support_vector, build_causal_admissibility_vector

ROOT = Path(__file__).resolve().parents[3]
CODE_HASH = "0" * 64


def estimate(method: str, temporal: str, effective: str, first_valid: str, causal: bool) -> dict:
    return build_estimate(
        method_id=method, family_id=f"F-{method}", config_id=f"C-{method}", temporal_class=temporal,
        state="ESTIMATED", candidate_onset_time=effective, effective_time=effective,
        confirmation_time=first_valid, first_valid_time=first_valid, evaluation_cutoff="2020-01-01T01:00:00Z",
        causal_admissibility=causal,
    )


def test_support_vector_is_complete_non_scalar_and_separate_from_causality() -> None:
    planes = {name: {"state": "PRESERVED"} for name in SUPPORT_PLANES}
    vector = build_boundary_support_vector(region_id="r", estimand="CONSENSUS_BOUNDARY_DISCOVERY", planes=planes,
                                           projection_ids=["p"], universe_id="u")
    causal = build_causal_admissibility_vector(
        region_id="r", estimates=[
            estimate("B1", "ONLINE_CAUSAL", "2020-01-01T00:10:00Z", "2020-01-01T00:10:00Z", True),
            estimate("B2", "CONFIRMATION_DELAYED", "2020-01-01T00:10:00Z", "2020-01-01T00:12:00Z", True),
            estimate("B3", "RETROSPECTIVE", "2020-01-01T00:10:00Z", "2020-01-01T00:30:00Z", False),
        ],
    )
    assert vector["scalar_score"] is None and causal["retrospective_causal_count"] == 0
    assert causal["entries"][-1]["evidence_role"] == "SUPPORT_ONLY"
    planes["score"] = 1
    with pytest.raises(CBSContractError, match="NO_VOTE_NO_AVERAGE"):
        build_boundary_support_vector(region_id="r", estimand="CONSENSUS_BOUNDARY_DISCOVERY", planes=planes,
                                      projection_ids=["p"], universe_id="u")


def test_causal_vector_rejects_backdating_and_retrospective_join() -> None:
    raw = estimate("B1", "ONLINE_CAUSAL", "2020-01-01T00:10:00Z", "2020-01-01T00:10:00Z", True)
    raw["first_valid_time"] = "2020-01-01T00:09:00Z"
    with pytest.raises(CBSContractError, match="FVT_BACKDATE_ATTEMPT"):
        build_causal_admissibility_vector(region_id="r", estimates=[raw])
    raw = estimate("B3", "RETROSPECTIVE", "2020-01-01T00:10:00Z", "2020-01-01T00:30:00Z", False)
    raw["causal_admissibility"] = True
    with pytest.raises(CBSContractError, match="RETROSPECTIVE_CAUSAL_JOIN_FORBIDDEN"):
        build_causal_admissibility_vector(region_id="r", estimates=[raw])


def null_manifest(control_class: str) -> dict:
    return build_null_execution_manifest(
        control_id=f"n-{control_class}", control_class=control_class, algorithm_id="reference-v1", code_hash=CODE_HASH,
        dependency_ids=["stdlib"], initialization={"mode": "fixed"}, seed=7, source_segment_lengths=[100],
        break_censor_policy="PRESERVE_TYPED_BREAKS_AND_CENSORS", randomisation_rule="DETERMINISTIC_REFERENCE_RULE",
        preserved_structures=["DECLARED_LOWER_ORDER"], destroyed_structures=["BOUNDARY_ALIGNMENT"],
        retained_dependence=["WITHIN_BLOCK"], adequacy_invalidators=["DEGENERATE_OUTPUT"], frozen_before_results=True,
    )


def test_control_coverage_requires_all_classes_and_exact_null_identity() -> None:
    manifests = [null_manifest(name) for name in sorted(REQUIRED_CONTROL_CLASSES)]
    assert validate_control_coverage(manifests)["complete"] is True
    assert assess_null_adequacy(manifest=manifests[0], output_complete=True, invalidators_observed=[])["adequate"] is True
    with pytest.raises(CBSContractError, match="MISSING"):
        validate_control_coverage(manifests[:-1])
    with pytest.raises(CBSContractError, match="POST_RESULT_NULL_SELECTION"):
        build_null_execution_manifest(
            control_id="post", control_class="NO_SEGMENTATION", algorithm_id="a", code_hash=CODE_HASH,
            dependency_ids=[], initialization={}, seed=None, source_segment_lengths=[1], break_censor_policy="typed",
            randomisation_rule="none", preserved_structures=[], destroyed_structures=[], retained_dependence=[],
            adequacy_invalidators=[], frozen_before_results=False,
        )


def test_dossier_disagreement_uncertainty_and_concordance_are_fail_honest() -> None:
    disagreement = build_method_disagreement_record(region_id="r", clusters=[{"cluster_id":"d","methods":["B1","B3"]}],
                                                     typed_source_events=[{"classification":"SOURCE_GAP","counted_as_disagreement":False}])
    uncertainty = build_uncertainty_record(region_id="r", topology={"split":1}, displacement_surface_ids=["s"],
                                           disagreement_record_id=disagreement["method_disagreement_record_id"])
    dossier = build_evidence_dossier(region_id="r", evidence_refs={name: [] for name in ("supporting","contradicting","null","missing","transport")},
                                     support_vector_id="sv", causal_vector_id="cv")
    surface = build_concordance_surface(estimand="REFERENCE_BOUNDARY_AUDIT", rows=[{"family":"B1","state":"UNMATCHED"}],
                                        universe_id="u", matched_support_id="m", full_population_id="f")
    assert uncertainty["canonical_timestamp"] is None and dossier["content_addressed_references_only"]
    assert surface["non_probabilistic"] and surface["causal_claim_effect"] == "NONE"
    with pytest.raises(CBSContractError, match="SOURCE_GAP_NOT_METHOD_DISAGREEMENT"):
        build_method_disagreement_record(region_id="r", clusters=[], typed_source_events=[{"classification":"SOURCE_GAP","counted_as_disagreement":True}])


def test_replay_restart_worker_order_and_hash_seed_are_logically_equivalent() -> None:
    rows = [{"id":"a","state":"NO_ESTIMATE"},{"id":"b","state":"ESTIMATED"}]
    receipt = build_replay_receipt(fresh_outputs=rows, restart_outputs=list(reversed(rows)),
                                   worker_order_outputs=list(reversed(rows)), hash_seed_outputs=rows, checkpoint_ids=["cp1"])
    assert receipt["fresh_restart_equal"] and receipt["cross_process_hash_seed_worker_order_equal"]
    with pytest.raises(CBSContractError, match="CHECKPOINT_DIVERGENCE"):
        build_replay_receipt(fresh_outputs=rows, restart_outputs=rows[:1], worker_order_outputs=rows,
                             hash_seed_outputs=rows, checkpoint_ids=["cp1"])


def test_capacity_preserves_complete_declared_surface_and_artifacts() -> None:
    scope = {"population":10,"methods":5,"configurations":2,"tolerances":2,"representations":1,"nulls":6,"opportunities":10}
    required = ["estimates","no_estimates","correspondence","disagreement"]
    receipt = build_capacity_receipt(declared=scope, executed=scope, capacity_limit=2000,
                                     retained_artifact_families=required, required_artifact_families=required)
    assert receipt["capacity_status"] == "PASS" and not receipt["scope_drops"]
    truncated = dict(scope); truncated["methods"] = 4
    with pytest.raises(CBSContractError, match="CAPACITY_EXCEEDED"):
        build_capacity_receipt(declared=scope, executed=truncated, capacity_limit=2000,
                               retained_artifact_families=required, required_artifact_families=required)


def test_all_28_adversarial_fixtures_are_machine_bound_and_enforced() -> None:
    registry = json.loads((ROOT/"fixtures/research_operations/cbs/wp5/CBSI_WP5_ADVERSARIAL_FIXTURE_REGISTRY_v0_1.json").read_text())
    by_id = {row["id"]: row for row in registry["fixtures"]}
    assert registry["mandatory_fixture_count"] == len(by_id) == 28
    assert set(by_id) == set(AV_DISPOSITIONS)
    assert all(by_id[key]["required_disposition"] == value for key, value in AV_DISPOSITIONS.items())
    assert all(adjudicate_fixture(key, False)["result"] == "PASS_ATTACK_BLOCKED" for key in by_id)
    with pytest.raises(CBSContractError, match="CBSI_G1_SYNTH_BLOCK:CBS-AV01:HARD_FAIL"):
        adjudicate_fixture("CBS-AV01", True)


def test_amendment_review_independence_and_temporal_diversity_interlocks() -> None:
    assert classify_amendment(changed_fields=["documentation_path"], semantic_identity_proved=True) == "MECHANICAL_NON_MEANING"
    assert classify_amendment(changed_fields=["tolerance"], semantic_identity_proved=True) == "MEANING_BEARING_SUCCESSOR"
    with pytest.raises(CBSContractError, match="INDEPENDENT_REVIEW_FAIL"):
        validate_independent_review(implementation_author="author", reviewer="author", fresh_process=True, conversation_state_used=False)
    methods = [{"temporal_class":"OWNER_DEFINED_ONLINE_CAUSAL","availability":"AVAILABLE"},
               {"temporal_class":"ONLINE_CAUSAL","availability":"AVAILABLE"}]
    with pytest.raises(CBSContractError, match="NOT_EVALUABLE:MINIMUM_TEMPORAL_CLASS_DIVERSITY"):
        validate_temporal_diversity(methods, broad_claim_requested=True)

from __future__ import annotations

from typing import Callable, Mapping, Any

from ovc.research_operations.ec1_path1 import DependenceEdge, EvidenceDependenceGraph
from .assurance import evaluate_reference_equivalence
from .algebra import (
    build_claim_dependency_manifest,
    build_scientific_challenge_vector,
    evaluate_scientific_disposition,
)
from .boundary import (
    build_tolerance_contract,
    fit_blind_independent_segmentation,
    match_boundaries_one_to_one,
)
from .contracts import PRSCContractError
from .dependence import build_candidate_dependence_profile
from .multiplicity import (
    build_hypothesis_family_registry,
    build_multiplicity_method_pack,
    enforce_review_capacity,
)
from .reference import build_reference_method_pack
from .replication import (
    ExposureState,
    ReplicationFirewallError,
    apply_exposure,
    assert_exposure_monotone,
)
from .representation import build_candidate_invariant_core, build_invariance_contract
from .temporal import build_context_challenge_pack, build_temporal_context_stability_matrix


class PRSCAdversarialConformanceError(ValueError):
    pass


def _result(fixture_id: str, expected_behavior: str, observed: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "fixture_id": fixture_id,
        "status": "PASS",
        "expected_behavior": expected_behavior,
        "observed": dict(observed),
        "authority_effect": "NONE",
    }


def _assert_frozen_family_membership(family_registry: Mapping[str, Any], proposed_hypothesis_ids: list[str]) -> None:
    declared = {str(row["hypothesis_id"]) for row in family_registry.get("hypotheses", [])}
    proposed = {str(value) for value in proposed_hypothesis_ids}
    if proposed != declared:
        raise PRSCAdversarialConformanceError("PRSC_POST_HOC_FAMILY_REDEFINITION_BLOCK")


def _confirmatory_status(*, e1_decision_bearing_inspected: bool, preregistration_frozen: bool) -> str:
    if e1_decision_bearing_inspected and not preregistration_frozen:
        return "DENIED"
    return "ELIGIBLE"


def _resolve_prsc_append_authority(*, greal_present: bool, explicit_prsc_append_authority: bool) -> str:
    if explicit_prsc_append_authority:
        return "PASS"
    if greal_present:
        return "BLOCK"
    return "BLOCK"


def _av01() -> dict[str, Any]:
    ids = [f"U{i:03d}" for i in range(200)]
    edges = []
    for start in (0, 100):
        for index in range(start, start + 99):
            edges.append(DependenceEdge(ids[index], ids[index + 1], "COMMON_POPULATION_UNIT_ANCESTRY"))
    profile = build_candidate_dependence_profile(EvidenceDependenceGraph(tuple(edges)), ids)
    if profile["owner_component_count"] != 2 or profile["independence_claim"] != "NOT_ESTABLISHED":
        raise PRSCAdversarialConformanceError("AV-PRSC-01 failed")
    return _result(
        "AV-PRSC-01",
        "NO_200_INDEPENDENT_EVIDENCE_CLAIM",
        {"owner_component_count": 2, "independence_claim": profile["independence_claim"]},
    )


def _av02() -> dict[str, Any]:
    profile = build_candidate_dependence_profile(EvidenceDependenceGraph(tuple()), ["U1", "U2"])
    if profile["no_edge_semantics"] != "INDEPENDENCE_UNKNOWN":
        raise PRSCAdversarialConformanceError("AV-PRSC-02 failed")
    return _result(
        "AV-PRSC-02",
        "NO_INDEPENDENCE_INFERENCE_FROM_GRAPH_ABSENCE",
        {
            "no_edge_semantics": profile["no_edge_semantics"],
            "independence_claim": profile["independence_claim"],
        },
    )


def _av03() -> dict[str, Any]:
    rejected = False
    try:
        build_reference_method_pack(method_pack_id="AV03.BAD", primary_method="IID_SHUFFLE")
    except PRSCContractError:
        rejected = True
    pack = build_reference_method_pack(method_pack_id="AV03.GOOD")
    if not rejected or not pack["reference_first"]:
        raise PRSCAdversarialConformanceError("AV-PRSC-03 failed")
    return _result(
        "AV-PRSC-03",
        "WEAK_NULL_NOT_SOLE_FREEZE_FACING_REFERENCE",
        {"primary_method": pack["primary_method"], "weak_null_rejected_as_primary": rejected},
    )


def _av04() -> dict[str, Any]:
    rejected = False
    try:
        build_reference_method_pack(
            method_pack_id="AV04.BAD",
            primary_method="HAC_EXPLICIT_ORDERED_SECONDARY",
        )
    except PRSCContractError:
        rejected = True
    pack = build_reference_method_pack(
        method_pack_id="AV04.GOOD",
        secondary_methods=["HAC_EXPLICIT_ORDERED_SECONDARY"],
    )
    if not rejected or pack["primary_method"] != "DEPENDENCY_PRESERVING_BLOCK_RESAMPLE":
        raise PRSCAdversarialConformanceError("AV-PRSC-04 failed")
    return _result(
        "AV-PRSC-04",
        "NO_POST_HOC_CHALLENGER_PROMOTION",
        {
            "primary_method": pack["primary_method"],
            "post_hoc_challenger_promotion_rejected": rejected,
        },
    )


def _av05() -> dict[str, Any]:
    contract = build_invariance_contract(
        contract_id="AV05",
        invariant_dimensions=["shape"],
        non_invariant_dimensions=["magnitude"],
    )
    core = build_candidate_invariant_core(
        {
            "metric": ["shape", "magnitude"],
            "ordinal": ["shape"],
        }
    )
    if core["core"] != ["shape"] or "magnitude" not in core["shell"]:
        raise PRSCAdversarialConformanceError("AV-PRSC-05 failed")
    return _result(
        "AV-PRSC-05",
        "INTERPRET_THROUGH_INVARIANCE_CONTRACT",
        {
            "invariant_core": core["core"],
            "shell": core["shell"],
            "contract_non_invariant": contract["non_invariant_dimensions"],
        },
    )


def _av06() -> dict[str, Any]:
    context = build_context_challenge_pack(pack_id="AV06", context_dimensions=["session"])
    matrix = build_temporal_context_stability_matrix(
        time_block_ids=["T1", "T2"],
        context_values=["A", "B"],
        rows=[
            {"time_block_id": "T1", "context_value": "A", "state": "SUPPORTED"},
            {"time_block_id": "T1", "context_value": "B", "state": "NOT_EVALUABLE"},
            {"time_block_id": "T2", "context_value": "A", "state": "SUPPORTED"},
            {"time_block_id": "T2", "context_value": "B", "state": "SUPPORTED"},
        ],
    )
    if context["causal_claim"] or matrix["structural_drift_inferred"]:
        raise PRSCAdversarialConformanceError("AV-PRSC-06 failed")
    return _result(
        "AV-PRSC-06",
        "CONDITIONAL_STABILITY_WITHOUT_CAUSAL_CLAIM",
        {
            "context_role": context["context_role"],
            "causal_claim": context["causal_claim"],
            "structural_drift_inferred": matrix["structural_drift_inferred"],
        },
    )


def _av07() -> dict[str, Any]:
    blocked = False
    try:
        fit_blind_independent_segmentation(
            [
                {"position": 0, "value": 1, "canonical_episode_id": "E1"},
                {"position": 1, "value": 3},
            ],
            method_pack_ref="AV07.BLIND",
            threshold=1,
        )
    except PRSCContractError:
        blocked = True
    if not blocked:
        raise PRSCAdversarialConformanceError("AV-PRSC-07 failed")
    return _result(
        "AV-PRSC-07",
        "BLOCK_BLIND_FIT_INTEGRITY",
        {"owner_label_read_attempt_blocked": blocked},
    )


def _av08() -> dict[str, Any]:
    tolerance = build_tolerance_contract(
        contract_id="AV08",
        early_tolerance=2,
        late_tolerance=2,
        position_unit="INDEX",
    )
    ledger = match_boundaries_one_to_one(
        canonical_boundaries=[
            {"canonical_boundary_id": "C1", "position": 10},
            {"canonical_boundary_id": "C2", "position": 11},
            {"canonical_boundary_id": "C3", "position": 12},
        ],
        challenger_boundaries=[{"challenger_boundary_id": "X1", "position": 11}],
        tolerance_contract=tolerance,
    )
    if ledger["matched_count"] != 1 or ledger["multiple_confirmation_claim"]:
        raise PRSCAdversarialConformanceError("AV-PRSC-08 failed")
    return _result(
        "AV-PRSC-08",
        "NO_TRIPLE_CONFIRMATION",
        {
            "matched_count": ledger["matched_count"],
            "unmatched_canonical_count": len(ledger["unmatched_canonical_boundary_ids"]),
            "multiple_confirmation_claim": ledger["multiple_confirmation_claim"],
        },
    )


def _av09() -> dict[str, Any]:
    family = build_hypothesis_family_registry(
        family_id="AV09",
        hypotheses=[
            {"hypothesis_id": f"H{i:03d}", "semantic_key": f"K{i:03d}"}
            for i in range(300)
        ],
    )
    attempted = [f"H{i:03d}" for i in range(12)]
    blocked = False
    try:
        _assert_frozen_family_membership(family, attempted)
    except PRSCAdversarialConformanceError:
        blocked = True
    pack = build_multiplicity_method_pack(method_pack_id="AV09.M", familywise_alpha="0.05")
    if not blocked or pack["family_redefinition_after_results"] != "FORBIDDEN":
        raise PRSCAdversarialConformanceError("AV-PRSC-09 failed")
    return _result(
        "AV-PRSC-09",
        "BLOCK_POST_HOC_FAMILY_REDEFINITION",
        {
            "declared_count": family["declared_hypothesis_count"],
            "attempted_count": len(attempted),
            "redefinition_blocked": blocked,
        },
    )


def _av10() -> dict[str, Any]:
    family = build_hypothesis_family_registry(
        family_id="AV10",
        hypotheses=[
            {"hypothesis_id": f"H{i:03d}", "semantic_key": f"K{i:03d}"}
            for i in range(400)
        ],
    )
    capacity = enforce_review_capacity(
        family_registry=family,
        reviewed_hypothesis_ids=[f"H{i:03d}" for i in range(50)],
        capacity_limit=50,
    )
    if capacity["status"] != "REVIEW_CAPACITY_EXCEEDED" or capacity["hidden_top_n_allowed"]:
        raise PRSCAdversarialConformanceError("AV-PRSC-10 failed")
    return _result(
        "AV-PRSC-10",
        "REVIEW_CAPACITY_EXCEEDED_HIDDEN_TOP_N_BLOCK",
        {
            "declared_count": capacity["declared_count"],
            "reviewed_count": capacity["reviewed_count"],
            "review_status": capacity["status"],
            "hidden_top_n_allowed": capacity["hidden_top_n_allowed"],
        },
    )


def _av11() -> dict[str, Any]:
    exposed = apply_exposure(ExposureState(), "SUMMARY")
    rollback_blocked = False
    try:
        assert_exposure_monotone(exposed, ExposureState())
    except ReplicationFirewallError:
        rollback_blocked = True
    if not exposed.contaminated or not rollback_blocked:
        raise PRSCAdversarialConformanceError("AV-PRSC-11 failed")
    return _result(
        "AV-PRSC-11",
        "EXPOSURE_MARKED_IRREVERSIBLE",
        {"contaminated": exposed.contaminated, "rollback_blocked": rollback_blocked},
    )


def _av12() -> dict[str, Any]:
    manifest = build_claim_dependency_manifest(candidate_ref="AV12", population_family="P1A")
    states: dict[str, str] = {}
    for dimension in manifest["required_dimensions"]:
        states[dimension] = "NON_FATAL_SUPPORT"
    for dimension in manifest["scope_condition_dimensions"]:
        states[dimension] = "NON_FATAL_SUPPORT"
    for dimension in manifest["advisory_dimensions"]:
        states[dimension] = "NOT_APPLICABLE"
    for dimension in manifest["non_applicable_dimensions"]:
        states[dimension] = "NOT_APPLICABLE"
    states["reference"] = "FATAL_TO_CURRENT_CLAIM"
    vector = build_scientific_challenge_vector(candidate_ref="AV12", dimension_states=states)
    disposition = evaluate_scientific_disposition(
        challenge_vector=vector,
        claim_dependency_manifest=manifest,
    )
    if disposition["disposition"] != "REJECT_CURRENT_CLAIM" or disposition["score"] is not None:
        raise PRSCAdversarialConformanceError("AV-PRSC-12 failed")
    return _result(
        "AV-PRSC-12",
        "FATAL_CONTRADICTION_WINS_NO_COMPENSATION",
        {
            "disposition": disposition["disposition"],
            "precedence": disposition["precedence_hit"],
            "score": disposition["score"],
            "majority_vote": disposition["majority_vote"],
        },
    )


def _av13() -> dict[str, Any]:
    status = _confirmatory_status(
        e1_decision_bearing_inspected=True,
        preregistration_frozen=False,
    )
    if status != "DENIED":
        raise PRSCAdversarialConformanceError("AV-PRSC-13 failed")
    return _result(
        "AV-PRSC-13",
        "CONFIRMATORY_STATUS_DENIED",
        {
            "e1_decision_bearing_inspected": True,
            "preregistration_frozen": False,
            "confirmatory_status": status,
        },
    )


def _av14() -> dict[str, Any]:
    resolution = _resolve_prsc_append_authority(
        greal_present=True,
        explicit_prsc_append_authority=False,
    )
    if resolution != "BLOCK":
        raise PRSCAdversarialConformanceError("AV-PRSC-14 failed")
    return _result(
        "AV-PRSC-14",
        "AUTHORITY_RESOLUTION_BLOCK",
        {
            "greal_present": True,
            "explicit_prsc_append_authority": False,
            "authority_resolution": resolution,
        },
    )


def _av15() -> dict[str, Any]:
    result = evaluate_reference_equivalence(
        "multiplicity",
        [1],
        lambda value: {"adjusted": value},
        lambda value: {"adjusted": value + 1},
    )[0]
    if result.status != "MISMATCH_QUARANTINE_OPTIMIZED":
        raise PRSCAdversarialConformanceError("AV-PRSC-15 failed")
    return _result(
        "AV-PRSC-15",
        "OPTIMIZED_PATH_QUARANTINED_REFERENCE_REMAINS_ORACLE",
        {
            "mismatch_detected": True,
            "optimized_path": "QUARANTINED",
            "reference_path": "ORACLE",
        },
    )


def build_wp1_wp7_adversarial_handlers() -> dict[str, Callable[[], Mapping[str, Any]]]:
    return {
        "AV-PRSC-01": _av01,
        "AV-PRSC-02": _av02,
        "AV-PRSC-03": _av03,
        "AV-PRSC-04": _av04,
        "AV-PRSC-05": _av05,
        "AV-PRSC-06": _av06,
        "AV-PRSC-07": _av07,
        "AV-PRSC-08": _av08,
        "AV-PRSC-09": _av09,
        "AV-PRSC-10": _av10,
        "AV-PRSC-11": _av11,
        "AV-PRSC-12": _av12,
        "AV-PRSC-13": _av13,
        "AV-PRSC-14": _av14,
        "AV-PRSC-15": _av15,
    }

from __future__ import annotations

import pytest

from ovc.research_operations.prsc.contracts import PRSCContractError
from ovc.research_operations.prsc.representation import (
    build_candidate_invariant_core,
    build_invariance_contract,
    build_population_crosswalk,
    build_representation_challenge_pack,
    directional_correspondence,
)
from ovc.research_operations.prsc.temporal import (
    build_context_challenge_pack,
    build_temporal_challenge_pack,
    build_temporal_context_stability_matrix,
    build_temporal_support_profile,
    leave_one_block_out_support,
    within_discovery_forward_support,
)


def test_representation_pack_has_no_winner_and_preserves_base() -> None:
    contract = build_invariance_contract(contract_id="INV.1", invariant_dimensions=["membership"])
    pack = build_representation_challenge_pack(
        pack_id="REP.1",
        base_representation_ref="DIRECT_STRUCTURAL_CANONICAL_v1",
        invariance_contract_ref=contract["semantic_sha256"],
        challengers=[{"challenger_id": "ordinal", "representation_ref": "ORDINAL.v1", "method_pack_ref": "MP.ORD.v1"}],
    )
    assert pack["selection_policy"] == "NO_WINNER"
    assert pack["base_representation_immutable"] is True
    assert pack["sri_scientific_authority"] == "NONE"
    with pytest.raises(PRSCContractError, match="HIDDEN_SELECTION"):
        build_representation_challenge_pack(
            pack_id="REP.BAD", base_representation_ref="BASE", invariance_contract_ref="INV",
            challengers=[{"challenger_id":"x","representation_ref":"X","method_pack_ref":"M","winner":True}],
        )


def test_invariance_contract_rejects_role_collision() -> None:
    with pytest.raises(PRSCContractError, match="DIMENSION_COLLISION"):
        build_invariance_contract(contract_id="INV.BAD", invariant_dimensions=["scale"], nuisance_dimensions=["scale"])


def test_crosswalk_requires_complete_directional_accounting() -> None:
    crosswalk = build_population_crosswalk(
        base_unit_ids=["a", "b", "c"],
        challenger_rows=[
            {"base_unit_id":"a","challenger_unit_ids":["x","y"],"status":"SPLIT"},
            {"base_unit_id":"b","challenger_unit_ids":["z"],"status":"MERGE"},
            {"base_unit_id":"c","challenger_unit_ids":[],"status":"NOT_COMPARABLE"},
        ],
    )
    assert crosswalk["complete_accounting"] is True
    assert crosswalk["identity_claim"] is False
    with pytest.raises(PRSCContractError, match="ACCOUNTING_MISSING"):
        build_population_crosswalk(base_unit_ids=["a", "b"], challenger_rows=[{"base_unit_id":"a","challenger_unit_ids":["x"],"status":"MATCH"}])


def test_directional_correspondence_preserves_split_merge_and_no_identity() -> None:
    result = directional_correspondence(
        {"s1":["a","b"], "s2":["c"]},
        {"t1":["a"], "t2":["b"], "t3":["c","d"]},
    )
    assert result["identity_claim"] is False
    assert result["records"][0]["status"] == "AMBIGUOUS"
    assert result["records"][1]["status"] == "SOURCE_MERGES_INTO_TARGET"


def test_invariant_core_refuses_universal_claim_when_one_view_failed() -> None:
    complete = build_candidate_invariant_core({"base":["a","b"], "alt":["b","c"]})
    assert complete["core"] == ["b"]
    assert complete["shell"] == ["a", "c"]
    assert complete["universal_claim"] is True
    partial = build_candidate_invariant_core({
        "base":{"status":"EVALUABLE","features":["a","b"]},
        "alt":{"status":"FAILED","features":[]},
    })
    assert partial["state"] == "PARTIAL_NOT_UNIVERSAL"
    assert partial["universal_claim"] is False


def test_temporal_pack_support_lobo_and_forward_support_are_nonreplicative() -> None:
    pack = build_temporal_challenge_pack(
        pack_id="TIME.1",
        year_blocks={"2021":["a"], "2022":["b"]},
        fixed_blocks={"F1":["c"]},
    )
    assert pack["selection_policy"] == "NO_BEST_BLOCK"
    profile = build_temporal_support_profile(
        declared_block_ids=["2021", "2022", "F1"],
        rows=[
            {"block_id":"2021","state":"SUPPORTED"},
            {"block_id":"2022","state":"NOT_EVALUABLE"},
            {"block_id":"F1","state":"NOT_SUPPORTED"},
        ],
    )
    assert profile["total_count"] == 3
    assert profile["complete_accounting"] is True
    assert len(leave_one_block_out_support(profile)) == 3
    forward = within_discovery_forward_support(profile, ordered_block_ids=["2021", "2022", "F1"])
    assert all(item["replication_claim"] is False for item in forward)
    assert all(item["evidence_class"] == "WITHIN_DISCOVERY_SUPPORT_DIAGNOSTIC" for item in forward)


def test_context_is_stratifier_only() -> None:
    pack = build_context_challenge_pack(pack_id="CTX.1", context_dimensions=["session", "weekday"])
    assert pack["context_role"] == "STRATIFIER_ONLY"
    assert pack["structural_identity_effect"] == "NONE"
    assert pack["causal_claim"] is False


def test_time_context_matrix_is_cartesian_and_separates_evaluability_drift() -> None:
    matrix = build_temporal_context_stability_matrix(
        time_block_ids=["2021", "2022"],
        context_values=["LONDON", "NY"],
        rows=[
            {"time_block_id":"2021","context_value":"LONDON","state":"SUPPORTED"},
            {"time_block_id":"2021","context_value":"NY","state":"SUPPORTED"},
            {"time_block_id":"2022","context_value":"LONDON","state":"NOT_EVALUABLE"},
        ],
    )
    assert matrix["expected_cell_count"] == 4
    assert len(matrix["cells"]) == 4
    assert matrix["cartesian_complete"] is True
    assert matrix["evaluability_or_composition_drift_detected"] is True
    assert matrix["structural_drift_inferred"] is False
    assert matrix["context_structural_identity_effect"] == "NONE"

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.prsc.boundary import (
    build_boundary_challenge_pack,
    build_boundary_preserving_control,
    build_c2e_internal_variant_correspondence,
    build_episode_partition_correspondence,
    build_morphology_invariant_core,
    build_tolerance_contract,
    fit_blind_independent_segmentation,
    match_boundaries_one_to_one,
)
from ovc.research_operations.prsc.contracts import PRSCContractError


ROOT = Path(__file__).resolve().parents[4]


def _tolerance() -> dict:
    return build_tolerance_contract(
        contract_id="TOL.1",
        early_tolerance=1,
        late_tolerance=2,
        position_unit="OBSERVATION_INDEX",
    )


def test_boundary_pack_preserves_canonical_identity_and_non_authority() -> None:
    pack = build_boundary_challenge_pack(
        pack_id="BOUNDARY.1",
        canonical_partition_ref="C2E.CANONICAL.v0.2",
        tolerance_contract_ref=_tolerance()["semantic_sha256"],
        challengers=[
            {"challenger_id": "internal", "challenger_class": "C2E_INTERNAL_VARIANT", "method_pack_ref": "MP.INT.v1"},
            {"challenger_id": "blind", "challenger_class": "BLIND_INDEPENDENT_SEGMENTATION", "method_pack_ref": "MP.BLIND.v1"},
        ],
    )
    assert pack["canonical_episode_identity_immutable"] is True
    assert pack["selection_policy"] == "NO_WINNER"
    assert pack["c2p_c25_c3_authority"] == "NONE"
    assert all(row["canonical_episode_identity_effect"] == "NONE" for row in pack["challengers"])


def test_tolerance_contract_rejects_post_hoc_or_negative_tolerance() -> None:
    with pytest.raises(PRSCContractError, match="TOLERANCE_INVALID"):
        build_tolerance_contract(contract_id="T", early_tolerance=-1, late_tolerance=1, position_unit="INDEX")
    with pytest.raises(PRSCContractError, match="TOLERANCE_INVALID"):
        build_tolerance_contract(
            contract_id="T", early_tolerance=1, late_tolerance=1,
            position_unit="INDEX", uncertainty_policy="FIT_TO_RESULTS",
        )


def test_blind_segmentation_cannot_read_c2e_boundaries_or_episode_labels() -> None:
    result = fit_blind_independent_segmentation(
        [
            {"position": 0, "value": 1},
            {"position": 1, "value": 1.2},
            {"position": 2, "value": 5},
        ],
        method_pack_ref="MP.BLIND.v1",
        threshold=2,
    )
    assert result["canonical_labels_read"] is False
    assert [row["position"] for row in result["boundaries"]] == ["1.5"]
    with pytest.raises(PRSCContractError, match="OWNER_LABEL_REACHABLE"):
        fit_blind_independent_segmentation(
            [
                {"position": 0, "value": 1, "canonical_episode_id": "E1"},
                {"position": 1, "value": 2},
            ],
            method_pack_ref="MP.BLIND.v1",
            threshold=1,
        )


def test_boundary_matching_is_one_to_one_directional_and_complete() -> None:
    ledger = match_boundaries_one_to_one(
        canonical_boundaries=[
            {"canonical_boundary_id": "c1", "position": 10},
            {"canonical_boundary_id": "c2", "position": 20},
        ],
        challenger_boundaries=[
            {"challenger_boundary_id": "x1", "position": 9},
            {"challenger_boundary_id": "x2", "position": 10.5},
            {"challenger_boundary_id": "x3", "position": 22},
        ],
        tolerance_contract=_tolerance(),
    )
    assert ledger["one_to_one"] is True
    assert ledger["complete_accounting"] is True
    assert ledger["matched_count"] == 2
    assert len({row["challenger_boundary_id"] for row in ledger["matches"]}) == 2
    assert ledger["unmatched_challenger_boundary_ids"] == ["x1"]
    assert [row["direction"] for row in ledger["matches"]] == ["LATE", "LATE"]
    assert ledger["multiple_confirmation_claim"] is False


def test_one_challenger_boundary_cannot_confirm_three_canonical_boundaries() -> None:
    ledger = match_boundaries_one_to_one(
        canonical_boundaries=[
            {"canonical_boundary_id": "c1", "position": 10},
            {"canonical_boundary_id": "c2", "position": 11},
            {"canonical_boundary_id": "c3", "position": 12},
        ],
        challenger_boundaries=[{"challenger_boundary_id": "x1", "position": 11}],
        tolerance_contract=build_tolerance_contract(
            contract_id="TOL.WIDE", early_tolerance=2, late_tolerance=2, position_unit="INDEX"
        ),
    )
    assert ledger["matched_count"] == 1
    assert len(ledger["unmatched_canonical_boundary_ids"]) == 2


def test_boundary_preserving_control_locks_positions() -> None:
    control = build_boundary_preserving_control(
        control_id="CONTROL.1",
        source_partition_ref="PARTITION.1",
        boundary_positions=[20, 10, 20],
        transform_ref="WITHIN_EPISODE_SIGN_FLIP.v1",
    )
    assert control["locked_boundary_positions"] == ["10", "20"]
    assert control["boundary_positions_immutable"] is True
    assert control["selection_effect"] == "NONE"


def test_episode_partition_correspondence_retains_split_merge_and_unmatched() -> None:
    split = build_episode_partition_correspondence(
        canonical_episodes=[
            {"canonical_episode_id": "c1", "start": 0, "end": 10},
            {"canonical_episode_id": "c2", "start": 10, "end": 20},
        ],
        challenger_episodes=[
            {"challenger_episode_id": "x1", "start": 0, "end": 5},
            {"challenger_episode_id": "x2", "start": 5, "end": 10},
            {"challenger_episode_id": "x3", "start": 12, "end": 18},
            {"challenger_episode_id": "x4", "start": 30, "end": 31},
        ],
    )
    assert split["rows"][0]["state"] == "SPLIT"
    assert split["rows"][1]["state"] == "PARTIAL"
    assert split["unmatched_challenger_episode_ids"] == ["x4"]
    assert split["canonical_episode_identity_effect"] == "NONE"

    merged = build_episode_partition_correspondence(
        canonical_episodes=[
            {"canonical_episode_id": "c1", "start": 0, "end": 5},
            {"canonical_episode_id": "c2", "start": 5, "end": 10},
        ],
        challenger_episodes=[{"challenger_episode_id": "x1", "start": 0, "end": 10}],
    )
    assert [row["state"] for row in merged["rows"]] == ["MERGE", "MERGE"]


def test_episode_partitions_reject_internal_overlap() -> None:
    with pytest.raises(PRSCContractError, match="PARTITION_OVERLAP"):
        build_episode_partition_correspondence(
            canonical_episodes=[
                {"canonical_episode_id": "c1", "start": 0, "end": 10},
                {"canonical_episode_id": "c2", "start": 9, "end": 11},
            ],
            challenger_episodes=[{"challenger_episode_id": "x1", "start": 0, "end": 11}],
        )


def test_c2e_internal_variant_never_replaces_owner_truth() -> None:
    record = build_c2e_internal_variant_correspondence(
        canonical_partition_ref="C2E.CANONICAL.v0.2",
        variant_ref="C2E.INTERNAL.CHALLENGER.v1",
        canonical_episodes=[{"canonical_episode_id": "c1", "start": 0, "end": 10}],
        variant_episodes=[{"challenger_episode_id": "x1", "start": 0, "end": 10}],
    )
    assert record["canonical_episode_identity_immutable"] is True
    assert record["variant_is_owner_truth"] is False
    assert record["canonical_episode_identity_effect"] == "NONE"


def test_morphology_core_refuses_universal_claim_if_a_view_failed() -> None:
    complete = build_morphology_invariant_core({
        "canonical": ["EXPANSION", "RETRACEMENT"],
        "blind": ["EXPANSION", "CONSOLIDATION"],
    })
    assert complete["core"] == ["EXPANSION"]
    assert complete["universal_claim"] is True
    partial = build_morphology_invariant_core({
        "canonical": {"status": "EVALUABLE", "morphologies": ["EXPANSION"]},
        "blind": {"status": "FAILED", "morphologies": []},
    })
    assert partial["state"] == "PARTIAL_NOT_UNIVERSAL"
    assert partial["universal_claim"] is False


def test_wp4_golden_fixture_reproduces_exact_boundary_trace() -> None:
    fixture = json.loads((
        ROOT / "fixtures/research_operations/ec1/prsc/wp4_boundary_segmentation_golden_v0_1.json"
    ).read_text(encoding="utf-8"))
    ledger = match_boundaries_one_to_one(
        canonical_boundaries=fixture["canonical_boundaries"],
        challenger_boundaries=fixture["challenger_boundaries"],
        tolerance_contract=_tolerance(),
    )
    assert ledger["matched_count"] == fixture["expected"]["matched_count"]
    assert [row["direction"] for row in ledger["matches"]] == fixture["expected"]["directions"]
    assert ledger["one_to_one"] is fixture["expected"]["one_to_one"]

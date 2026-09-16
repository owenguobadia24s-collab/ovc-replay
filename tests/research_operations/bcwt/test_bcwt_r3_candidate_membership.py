from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.bcwt.candidate import (
    CANDIDATE_GENERATION_ID,
    classify_membership,
    compile_membership_ledger,
    compile_occurrences,
)
from ovc.research_operations.bcwt.mechanical import BCWTValidationError
from ovc.research_operations.bcwt.opgs_r3_adapter import normalize_opgs_r3_accounts

FIXTURE = Path("fixtures/research_operations/bcwt/v0_1/candidate_membership_rows.json")


def rows():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_frozen_membership_rules_and_complete_denominator():
    ledger = compile_membership_ledger(rows(), expected_count=4)
    assert ledger["candidate_generation_id"] == CANDIDATE_GENERATION_ID
    assert ledger["expected_opportunities"] == ledger["actual_opportunities"] == 4
    assert [entry["state"] for entry in ledger["entries"]] == [
        "MATCH", "NON_MATCH", "AMBIGUOUS", "NOT_EVALUABLE"
    ]
    assert compile_occurrences(ledger) == [
        {"candidate_generation_id": CANDIDATE_GENERATION_ID, "population_unit_id": "u1"}
    ]


def test_d16_relation_change_is_match_without_numeric_threshold():
    row = rows()[2]
    row["d16_relation_after"] = "ABOVE"
    assert classify_membership(row)["state"] == "MATCH"


def test_replay_is_byte_identity_equivalent_at_digest_surface():
    first = compile_membership_ledger(rows(), expected_count=4)
    second = compile_membership_ledger(rows(), expected_count=4)
    assert first == second
    assert first["ledger_sha256"] == second["ledger_sha256"]


def test_incomplete_denominator_fails_closed():
    with pytest.raises(BCWTValidationError, match="complete denominator failure"):
        compile_membership_ledger(rows(), expected_count=5238)


def test_non_adjacent_or_cross_segment_source_fails_closed():
    non_adjacent = rows()[0]
    non_adjacent["end_sequence_id"] = 9
    with pytest.raises(BCWTValidationError, match="non-adjacent"):
        classify_membership(non_adjacent)

    cross_segment = rows()[0]
    cross_segment["d15_same_uninterrupted_segment"] = False
    with pytest.raises(BCWTValidationError, match="cross-segment"):
        classify_membership(cross_segment)


def test_outcome_bearing_input_is_forbidden():
    contaminated = rows()[0]
    contaminated["future_outcome"] = {"signed_return": 1}
    with pytest.raises(PermissionError, match="outcome-blind firewall"):
        classify_membership(contaminated)


def test_duplicate_population_units_fail_closed():
    duplicate = rows()
    duplicate[-1]["population_unit_id"] = duplicate[0]["population_unit_id"]
    with pytest.raises(BCWTValidationError, match="duplicate population_unit_id"):
        compile_membership_ledger(duplicate, expected_count=4)


def test_opgs_r3_adapter_preserves_unresolved_but_blocks_not_evaluable():
    def account(account_id, d10_state="NOT_OBSERVED", d14_state="UNRESOLVED"):
        distinctions = {
            key: {"state": "OBSERVED"} for key in ("D10", "D12", "D14", "D15", "D16")
        }
        distinctions["D10"]["state"] = d10_state
        distinctions["D14"]["state"] = d14_state
        return {
            "account_id": account_id,
            "segment": "1",
            "start_percept_ref": {"cutoff_fvt_ms": 1, "snapshot_id": "s0"},
            "end_percept_ref": {"cutoff_fvt_ms": 2, "snapshot_id": "s1"},
            "frame_account": {"local_relation_before": "OVERLAP", "local_relation_after": "ABOVE"},
            "distinctions": distinctions,
        }

    unresolved = normalize_opgs_r3_accounts([account("a")])[0]
    assert unresolved["d17_load_bearing_evaluable"] is True
    assert unresolved["d16_evaluable"] is True
    blocked = normalize_opgs_r3_accounts([account("b", d10_state="NOT_EVALUABLE")])[0]
    assert blocked["d17_load_bearing_evaluable"] is False

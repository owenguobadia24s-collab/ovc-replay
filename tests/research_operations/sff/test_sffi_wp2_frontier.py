from datetime import datetime, timedelta, timezone

import pytest

from ovc.research_operations.sff.core import ResearchFreezeFrontier, SFFContractError
from ovc.research_operations.sff.frontier import (
    StructuralAntecedent,
    assert_replay_equivalent,
    checkpoint,
    generate_one_step_frontier,
)


NOW = datetime(2026, 8, 27, 13, tzinfo=timezone.utc)


def _inputs():
    antecedent = StructuralAntecedent("a-1", "owner-fact-1", NOW, "SYNTHETIC_NODE", {"rank": 1})
    freeze = ResearchFreezeFrontier("freeze-1", NOW + timedelta(seconds=1), "synthetic-source", "auth-1")
    return antecedent, freeze


def test_one_step_generation_is_byte_deterministic_and_restart_equivalent() -> None:
    antecedent, freeze = _inputs()
    args = dict(
        antecedent=antecedent,
        freeze=freeze,
        grammar_identity="grammar-candidate-1",
        structural_labels=("CONTINUATION", "REVERSAL", "TERMINATION"),
        expected_owner_fact_id="owner-fact-1",
    )
    first = generate_one_step_frontier(**args)
    restarted = generate_one_step_frontier(**args)
    assert_replay_equivalent(first, restarted)
    assert checkpoint(first) == checkpoint(restarted)
    assert len({target.target_id for target in first.targets}) == 3
    assert first.source_mode == "SYNTHETIC_ONLY"


def test_identity_changes_only_with_meaning_bearing_payload() -> None:
    antecedent, freeze = _inputs()
    first = generate_one_step_frontier(
        antecedent=antecedent,
        freeze=freeze,
        grammar_identity="g-1",
        structural_labels=("A",),
        expected_owner_fact_id="owner-fact-1",
    )
    second = generate_one_step_frontier(
        antecedent=antecedent,
        freeze=freeze,
        grammar_identity="g-1",
        structural_labels=("B",),
        expected_owner_fact_id="owner-fact-1",
    )
    assert first.generation_id != second.generation_id
    with pytest.raises(SFFContractError, match="REPLAY_MISMATCH"):
        assert_replay_equivalent(first, second)


def test_owner_chronology_and_duplicate_targets_fail_closed() -> None:
    antecedent, freeze = _inputs()
    common = dict(antecedent=antecedent, freeze=freeze, grammar_identity="g-1")
    with pytest.raises(SFFContractError, match="OWNER"):
        generate_one_step_frontier(**common, structural_labels=("A",), expected_owner_fact_id="wrong")
    with pytest.raises(SFFContractError, match="unique"):
        generate_one_step_frontier(**common, structural_labels=("A", "A"), expected_owner_fact_id="owner-fact-1")
    leaking = StructuralAntecedent("a-2", "owner-fact-1", freeze.cutoff_at, "SYNTHETIC_NODE", {})
    with pytest.raises(SFFContractError):
        generate_one_step_frontier(
            antecedent=leaking,
            freeze=freeze,
            grammar_identity="g-1",
            structural_labels=("A",),
            expected_owner_fact_id="owner-fact-1",
        )

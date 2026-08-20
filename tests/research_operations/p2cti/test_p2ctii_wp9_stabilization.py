from __future__ import annotations

import copy

import pytest

from ovc.research_operations.p2cti.stabilization import (
    StabilizationError,
    build_shadow_observation,
    build_stabilization_ledger,
    evaluate_incidents,
)

GENERATION = "p2cti:generation:" + "a" * 64
FRONTIER = "p2cti:frontier:" + "b" * 64
COMMIT = "c" * 40
TREE = "d" * 40


def _observation(**overrides):
    kwargs = {
        "repository_commit": COMMIT,
        "repository_tree": TREE,
        "generation_id": GENERATION,
        "source_frontier_id": FRONTIER,
        "currentness_state": "CURRENT",
        "reference_optimized_equivalent": True,
        "protected_source_leak_count": 0,
        "index_integrity_ok": True,
        "warnings": [],
    }
    kwargs.update(overrides)
    return build_shadow_observation(**kwargs)


def test_clean_live_shadow_is_stable_but_never_activates_itself() -> None:
    observation = _observation()
    evaluation = evaluate_incidents(observation)
    assert observation["read_only_shadow"] is True
    assert observation["operational_reliance"] is False
    assert observation["index_integrity_ok"] is True
    assert evaluation["status"] == "PASS_SHADOW_STABLE"
    assert evaluation["incident_classes"] == []
    assert evaluation["automatic_activation"] is False
    assert evaluation["authority_effect"] == "NONE"


@pytest.mark.parametrize(
    ("overrides", "incident"),
    [
        ({"currentness_state": "STALE"}, "FALSE_CURRENTNESS"),
        ({"currentness_state": "UNRESOLVED"}, "SOURCE_FRONTIER_UNRESOLVED"),
        ({"reference_optimized_equivalent": False}, "REFERENCE_OPTIMIZED_DIVERGENCE"),
        ({"protected_source_leak_count": 1}, "PROTECTED_SOURCE_LEAK"),
        ({"index_integrity_ok": False}, "INDEX_CORRUPTION"),
    ],
)
def test_incident_triggers_require_requalification(overrides: dict, incident: str) -> None:
    evaluation = evaluate_incidents(_observation(**overrides))
    assert evaluation["status"] == "REQUALIFICATION_REQUIRED"
    assert incident in evaluation["incident_classes"]
    assert evaluation["automatic_activation"] is False


def test_stabilization_ledger_is_deterministic_and_binds_activation_gate() -> None:
    first = _observation(repository_commit="1" * 40, repository_tree="2" * 40)
    second = _observation(repository_commit="3" * 40, repository_tree="4" * 40)
    forward = build_stabilization_ledger([first, second])
    reverse = build_stabilization_ledger([second, first])
    assert forward == reverse
    assert forward["all_stable"] is True
    assert forward["activation_gate"] == "P2CTII-G-OBSERVABILITY-ACTIVATE"
    assert forward["operational_reliance"] is False
    assert forward["authority_effect"] == "NONE"


def test_mutated_observation_is_rejected() -> None:
    observation = _observation()
    mutated = copy.deepcopy(observation)
    mutated["protected_source_leak_count"] = 2
    with pytest.raises(StabilizationError, match="integrity"):
        build_stabilization_ledger([mutated])


def test_shadow_identity_and_warning_validation_fail_closed() -> None:
    with pytest.raises(StabilizationError, match="git SHA"):
        _observation(repository_commit="C" * 40)
    with pytest.raises(StabilizationError, match="warnings"):
        _observation(warnings=["DUP", "DUP"])

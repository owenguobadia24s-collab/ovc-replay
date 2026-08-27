from datetime import datetime, timedelta, timezone
import json

import pytest

from ovc.research_operations.sff.core import (
    AuthorityError,
    ChronologyError,
    ResearchFreezeFrontier,
    TargetComplexityBudget,
    TargetGrammarExposureManifest,
    canonical_bytes,
    content_identity,
    require_first_valid_chronology,
)
from ovc.research_operations.sff.owner import OwnerFact, OwnerResolver


NOW = datetime(2026, 8, 27, 12, tzinfo=timezone.utc)


def test_canonical_identity_is_order_and_process_stable() -> None:
    left = {"b": [2, 1], "a": {"z": True}}
    right = {"a": {"z": True}, "b": [2, 1]}
    assert canonical_bytes(left) == canonical_bytes(right)
    assert content_identity("sff-test", left) == content_identity("sff-test", right)
    assert json.loads(canonical_bytes(left)) == left


def test_chronology_is_strict_and_rejects_equality_or_future_leakage() -> None:
    require_first_valid_chronology(antecedent_at=NOW, cutoff_at=NOW + timedelta(microseconds=1))
    with pytest.raises(ChronologyError):
        require_first_valid_chronology(antecedent_at=NOW, cutoff_at=NOW)
    with pytest.raises(ChronologyError):
        require_first_valid_chronology(antecedent_at=NOW + timedelta(seconds=1), cutoff_at=NOW)


def test_freeze_and_target_contracts_preserve_non_grants() -> None:
    frontier = ResearchFreezeFrontier("f-1", NOW, "source-1", "authority-1")
    assert frontier.validation_state == "LOCKED_UNCONSUMED"
    manifest = TargetGrammarExposureManifest("m-1", "SINGLE_DECLARED", "grammar-1", True)
    assert manifest.activation_state == "CANDIDATE_ONLY_NOT_ACTIVE"
    assert TargetComplexityBudget("b-1", 10, 1, 3).deep_tree_state == "DEFERRED_NON_EXECUTABLE"
    with pytest.raises(AuthorityError):
        TargetComplexityBudget("b-2", 10, 2, 3)


def test_owner_resolver_fails_closed_for_every_unearned_state() -> None:
    good = OwnerFact("dep", "owner", "blob", "CURRENT", "AUTHORIZED_READ_ONLY")
    assert OwnerResolver([good]).resolve("dep") == good
    with pytest.raises(AuthorityError, match="MISSING"):
        OwnerResolver([]).resolve("dep")
    conflict = OwnerFact("dep", "other", "blob", "CURRENT", "AUTHORIZED_READ_ONLY")
    with pytest.raises(AuthorityError, match="CONFLICT"):
        OwnerResolver([good, conflict]).resolve("dep")
    with pytest.raises(AuthorityError, match="STALE"):
        OwnerResolver([OwnerFact("dep", "owner", "blob", "STALE", "AUTHORIZED_READ_ONLY")]).resolve("dep")
    with pytest.raises(AuthorityError, match="UNAUTHORIZED"):
        OwnerResolver([OwnerFact("dep", "owner", "blob", "CURRENT", "DENIED")]).resolve("dep")

from pathlib import Path

import pytest

from ovc.research_operations.sff.adversarial import (
    classify_feasibility,
    reconcile_population,
    run_adversarial_corpus,
    validate_atomic_freeze,
    validate_method_binding,
    validate_state_separation,
)
from ovc.research_operations.sff.core import SFFContractError


ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "fixtures/research_operations/sff/SFFI_WP6_ADVERSARIAL_CORPUS_v0_1.json"


def test_all_blocking_adversarial_fixtures_pass_without_weakening() -> None:
    report = run_adversarial_corpus(CORPUS)
    assert report["total"] == 31
    assert report["passed"] == 31
    assert report["blocked"] == 0
    assert {row["attack_id"] for row in report["results"]} >= {f"SFF-R1-A{index}" for index in range(25, 32)}


def test_atomic_freeze_and_method_binding_fail_closed() -> None:
    with pytest.raises(SFFContractError, match="HASH_MISMATCH"):
        validate_atomic_freeze({"atomic": True, "bundle_sha256": "a", "calculated_bundle_sha256": "b", "decision_fields_complete": True})
    with pytest.raises(SFFContractError, match="METHOD_BINDING"):
        validate_method_binding("preregistered", "executed")


def test_contamination_attrition_and_state_separation_are_typed() -> None:
    assert classify_feasibility(outcome_viewed=True) == "OUTCOME_EXPOSED_NONCONFIRMATORY"
    with pytest.raises(SFFContractError, match="ATTRITION"):
        reconcile_population(("a", "b"), {"a": "RESOLVED"})
    with pytest.raises(SFFContractError, match="STATE_TYPE"):
        validate_state_separation("PASS", "PASS")

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from ovc.research_operations.p1cdi.stabilization import (
    StabilizationError,
    build_shadow_observation,
    build_stabilization_ledger,
    evaluate_incidents,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = json.loads(
    (ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP10_STABILIZATION_FIXTURE_v0_1.json").read_text()
)


def _observation(**changes):
    kwargs = copy.deepcopy(FIXTURE["stable"])
    kwargs.update(changes)
    return build_shadow_observation(**kwargs)


def test_clean_current_shadow_is_stable_but_never_activates_itself() -> None:
    observation = _observation()
    evaluation = evaluate_incidents(observation)
    assert observation["read_only_shadow"] is True
    assert observation["operational_reliance"] is False
    assert observation["automatic_activation"] is False
    assert observation["authority_effect"] == "NONE"
    assert evaluation["status"] == "PASS_SHADOW_STABLE"
    assert evaluation["incident_classes"] == []
    assert evaluation["automatic_activation"] is False
    assert evaluation["authority_effect"] == "NONE"


@pytest.mark.parametrize("case", FIXTURE["incident_cases"], ids=lambda case: case["case_id"])
def test_every_declared_incident_requires_requalification(case: dict) -> None:
    evaluation = evaluate_incidents(_observation(**case["changes"]))
    assert evaluation["status"] == "REQUALIFICATION_REQUIRED"
    assert case["incident"] in evaluation["incident_classes"]
    assert evaluation["operational_reliance"] is False
    assert evaluation["automatic_activation"] is False


def test_stabilization_ledger_is_deterministic_and_binds_operator_activation_gate() -> None:
    first = _observation(repository_commit="1" * 40, repository_tree="2" * 40)
    second = _observation(repository_commit="3" * 40, repository_tree="4" * 40)
    forward = build_stabilization_ledger([first, second])
    reverse = build_stabilization_ledger([second, first])
    assert forward == reverse
    assert forward["all_stable"] is True
    assert forward["activation_gate"] == "P1CDII-G-OBSERVABILITY-ACTIVATE"
    assert forward["operational_reliance"] is False
    assert forward["automatic_activation"] is False
    assert forward["authority_effect"] == "NONE"


def test_mutated_observation_and_empty_ledger_fail_closed() -> None:
    observation = _observation()
    mutated = copy.deepcopy(observation)
    mutated["protected_source_leak_count"] = 1
    with pytest.raises(StabilizationError, match="integrity"):
        build_stabilization_ledger([mutated])
    with pytest.raises(StabilizationError, match="at least one"):
        build_stabilization_ledger([])


def test_identity_counts_boolean_and_warning_validation_fail_closed() -> None:
    with pytest.raises(StabilizationError, match="git SHA"):
        _observation(repository_commit="C" * 40)
    with pytest.raises(StabilizationError, match="SHA-256"):
        _observation(source_census_sha256="x" * 64)
    with pytest.raises(StabilizationError, match="non-negative integer"):
        _observation(expected_subject_count=-1)
    with pytest.raises(StabilizationError, match="boolean"):
        _observation(capacity_complete=1)
    with pytest.raises(StabilizationError, match="warnings"):
        _observation(warnings=["DUP", "DUP"])


def test_zero_subject_exact_court_scope_is_stable_not_invented_or_incomplete() -> None:
    observation = _observation(expected_subject_count=0, reconciled_subject_count=0)
    evaluation = evaluate_incidents(observation)
    assert evaluation["status"] == "PASS_SHADOW_STABLE"
    assert evaluation["incident_classes"] == []


def test_materialised_wp10_shadow_exactly_binds_current_court_evidence() -> None:
    observation_path = ROOT / "docs/programmes/p1cdi-v0-1/wp10/P1CDII_WP10_LIVE_SHADOW_OBSERVATION_v0_1.json"
    ledger_path = ROOT / "docs/programmes/p1cdi-v0-1/wp10/P1CDII_WP10_STABILIZATION_LEDGER_v0_1.json"
    census_path = ROOT / "records/research_operations/p1cdi/P1CDI_BOOTSTRAP_SOURCE_CENSUS_MANIFEST_v0_2.json"
    completeness_path = ROOT / "records/research_operations/p1cdi/P1CDI_BOOTSTRAP_SOURCE_COMPLETENESS_MANIFEST_v0_1.json"
    receipt_path = ROOT / "docs/programmes/p1cdi-v0-1/wp9/P1CDII_WP9_PHYSICAL_MATERIALISATION_RECEIPT_v0_1.json"

    observation = json.loads(observation_path.read_text())
    ledger = json.loads(ledger_path.read_text())
    census = json.loads(census_path.read_text())
    completeness = json.loads(completeness_path.read_text())
    receipt = json.loads(receipt_path.read_text())

    assert observation["repository_commit"] == receipt["merge_commit"]
    assert observation["repository_tree"] == receipt["merge_tree"]
    assert observation["source_census_id"] == census["census_id"]
    assert observation["source_completeness_manifest_id"] == completeness["manifest_id"]
    assert observation["source_census_sha256"] == hashlib.sha256(census_path.read_bytes()).hexdigest()
    assert observation["source_completeness_sha256"] == hashlib.sha256(completeness_path.read_bytes()).hexdigest()
    assert observation["expected_subject_count"] == census["expected_subject_count"] == 0
    assert observation["reconciled_subject_count"] == completeness["reconciled_subject_count"] == 0
    assert completeness["complete"] is True
    assert build_stabilization_ledger([observation]) == ledger


def test_wp10_schema_declares_closed_shadow_evaluation_and_ledger_contracts() -> None:
    schema = json.loads(
        (ROOT / "schemas/research_operations/p1cdi/p1cdi_stabilization_v0_1.schema.json").read_text()
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["oneOf"] == [
        {"$ref": "#/$defs/observation"},
        {"$ref": "#/$defs/evaluation"},
        {"$ref": "#/$defs/ledger"},
    ]
    assert schema["$defs"]["observation"]["additionalProperties"] is False
    assert schema["$defs"]["evaluation"]["additionalProperties"] is False
    assert schema["$defs"]["ledger"]["additionalProperties"] is False

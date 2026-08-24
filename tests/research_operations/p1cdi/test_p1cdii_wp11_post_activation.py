from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from ovc.research_operations.canonical import canonical_sha256
from ovc.research_operations.p1cdi.post_activation import (
    PostActivationError,
    build_operational_monitoring_ledger,
    build_operational_observation,
    build_rehearsal_record,
    evaluate_operational_incidents,
    rehearse_minimal_exact_intake,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/research_operations/p1cdi/P1CDII_WP11_POST_ACTIVATION_FIXTURE_v0_1.json"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _observation(**overrides):
    f = _fixture()
    values = {
        "repository_commit": f["repository_commit"],
        "repository_tree": f["repository_tree"],
        "source_census_id": f["source_census_id"],
        "source_census_sha256": f["source_census_sha256"],
        "source_completeness_manifest_id": f["source_completeness_manifest_id"],
        "source_completeness_sha256": f["source_completeness_sha256"],
        "expected_subject_count": f["expected_subject_count"],
        "reconciled_subject_count": f["reconciled_subject_count"],
        "currentness_state": "CURRENT",
        "reference_optimized_equivalent": True,
        "protected_source_leak_count": 0,
        "validation_leak_count": 0,
        "candidate_authority_survivor_count": 0,
        "source_identity_drift": False,
        "owner_semantic_conflict": False,
        "index_integrity_ok": True,
        "capacity_complete": True,
        "activation_receipt_ref": f["activation_receipt_ref"],
        "warnings": (),
    }
    values.update(overrides)
    return build_operational_observation(**values)


def _records():
    f = _fixture()["synthetic_rehearsal"]
    return [
        build_rehearsal_record(
            operation=operation,
            source_id=f["source_id"],
            generation_id=f["generation_id"],
            subject_ref=f"{f['subject_ref']}:{index}",
            evidence_sha256=f["evidence_sha256"],
        )
        for index, operation in enumerate(f["operations"], start=1)
    ]


def test_fixture_binds_exact_post_activation_frontier() -> None:
    f = _fixture()
    assert f["repository_commit"] == "4aac7376e60525b0c86b9f4577ce32790b0d98de"
    assert f["repository_tree"] == "f887aa0d709b723aa7b92abbc8a2e6ba0930cdf3"
    assert f["expected_subject_count"] == 0
    assert f["reconciled_subject_count"] == 0
    assert "P1CDII_G_OBSERVABILITY_ACTIVATE_ACTIVATION_RECEIPT" in f["activation_receipt_ref"]
    assert f["synthetic_rehearsal"]["operations"] == [
        "SOURCE_EXPLICIT_EXACT_INTAKE",
        "EXACT_DUPLICATE",
        "SAME_GENERATION_EVIDENCE_ATTACHMENT",
    ]
    assert f["authority_effect"] == "NONE"


def test_post_activation_observation_is_operational_read_only_and_stable() -> None:
    observation = _observation()
    assert observation["operational_reliance"] is True
    assert observation["read_only"] is True
    assert observation["durable_write_effect"] is False
    assert observation["expected_subject_count"] == 0
    assert observation["reconciled_subject_count"] == 0
    evaluation = evaluate_operational_incidents(observation)
    assert evaluation["status"] == "PASS_OPERATIONAL_STABLE"
    assert evaluation["incident_classes"] == []
    assert evaluation["continue_operational_reliance"] is True
    assert evaluation["automatic_authority_expansion"] is False
    assert evaluation["authority_effect"] == "NONE"


@pytest.mark.parametrize(
    ("overrides", "incident"),
    [
        ({"currentness_state": "STALE"}, "FALSE_CURRENTNESS"),
        ({"currentness_state": "UNRESOLVED"}, "SOURCE_FRONTIER_UNRESOLVED"),
        ({"reconciled_subject_count": 1}, "SOURCE_FRONTIER_UNRESOLVED"),
        ({"source_identity_drift": True}, "SOURCE_IDENTITY_DRIFT"),
        ({"owner_semantic_conflict": True}, "OWNER_SEMANTIC_CONFLICT"),
        ({"reference_optimized_equivalent": False}, "REFERENCE_OPTIMIZED_DIVERGENCE"),
        ({"protected_source_leak_count": 1}, "MODE_LEAK"),
        ({"validation_leak_count": 1}, "VALIDATION_LEAK"),
        ({"candidate_authority_survivor_count": 1}, "CANDIDATE_AUTHORITY_BYPASS"),
        ({"index_integrity_ok": False}, "INDEX_CORRUPTION"),
        ({"capacity_complete": False}, "CAPACITY_EXCEEDED"),
    ],
)
def test_incident_drills_fail_closed_to_requalification(overrides: dict, incident: str) -> None:
    evaluation = evaluate_operational_incidents(_observation(**overrides))
    assert incident in evaluation["incident_classes"]
    assert evaluation["status"] == "REQUALIFICATION_REQUIRED"
    assert evaluation["required_action"] == "DISABLE_RELIANCE_AND_REQUALIFY"
    assert evaluation["continue_operational_reliance"] is False
    assert evaluation["automatic_authority_expansion"] is False
    assert evaluation["durable_write_effect"] is False


def test_monitoring_ledger_is_order_independent_and_bounded() -> None:
    first = _observation()
    second = _observation(repository_commit="b" * 40, repository_tree="c" * 40)
    one = build_operational_monitoring_ledger([first, second])
    two = build_operational_monitoring_ledger([second, first])
    assert one == two
    assert one["all_stable"] is True
    assert one["operational_reliance_scope"] == "READ_ONLY_CURRENT_PROJECTION_EXACT_SCOPE_ONLY"
    assert one["durable_write_effect"] is False
    assert one["next_reserved_gate"] == "P1CDII-G-CONTINUOUS-INTAKE"


def test_minimal_exact_intake_rehearsal_is_deterministic_and_never_durable() -> None:
    records = _records()
    one = rehearse_minimal_exact_intake(records)
    two = rehearse_minimal_exact_intake(list(reversed(records)))
    assert one == two
    assert one["storage_scope"] == "EPHEMERAL_IN_MEMORY_ONLY"
    assert one["record_count"] == 3
    assert one["allowed_rehearsed_operations"] == [
        "EXACT_DUPLICATE",
        "SAME_GENERATION_EVIDENCE_ATTACHMENT",
        "SOURCE_EXPLICIT_EXACT_INTAKE",
    ]
    assert one["replay_equal"] is True
    assert one["durable_target"] is None
    assert one["durable_write_attempted"] is False
    assert one["durable_write_performed"] is False
    assert one["write_activation"] is False
    assert one["scientific_effect"] == "NONE"
    assert one["candidate_effect"] == "NONE"
    assert one["execution_authority"] == "NONE"
    assert one["next_reserved_gate"] == "P1CDII-G-CONTINUOUS-INTAKE"


def test_rehearsal_rejects_durable_sink_mutation_and_duplicate() -> None:
    records = _records()
    target = _fixture()["synthetic_rehearsal"]["forbidden_durable_target"]
    with pytest.raises(PostActivationError, match="durable targets are forbidden"):
        rehearse_minimal_exact_intake(records, durable_target=target)

    mutated = copy.deepcopy(records[0])
    mutated["subject_ref"] = "mutated"
    with pytest.raises(PostActivationError, match="content hash mismatch"):
        rehearse_minimal_exact_intake([mutated])

    with pytest.raises(PostActivationError, match="missing or duplicated"):
        rehearse_minimal_exact_intake([records[0], records[0]])


def test_rehearsal_rejects_write_activation_and_authority_effect() -> None:
    record = _records()[0]
    write_enabled = copy.deepcopy(record)
    write_enabled["write_activation"] = True
    write_enabled["content_sha256"] = canonical_sha256({k: v for k, v in write_enabled.items() if k != "content_sha256"})
    with pytest.raises(PostActivationError, match="write activation is forbidden"):
        rehearse_minimal_exact_intake([write_enabled])

    authority = copy.deepcopy(record)
    authority["authority_effect"] = "EXPANDED"
    authority["content_sha256"] = canonical_sha256({k: v for k, v in authority.items() if k != "content_sha256"})
    with pytest.raises(PostActivationError, match="forbidden authority or scientific effect"):
        rehearse_minimal_exact_intake([authority])

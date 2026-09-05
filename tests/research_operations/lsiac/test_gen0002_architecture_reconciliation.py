from __future__ import annotations

from pathlib import Path

from ovc.research_operations.lsiac.architecture_reconciliation_gen0002 import (
    AUTHORITY_EFFECT,
    DISPOSITION,
    SOURCE_REGISTER_MERGE_COMMIT,
    SOURCE_REGISTER_VIRTUAL_BUNDLE_ID,
    build_architecture_reconciliation,
    build_reconciliation_identity,
)

ROOT = Path(__file__).resolve().parents[3]
ALGORITHM_BLOB_SHA = "9559ccd584fd71d791aca154e854a6fd228fd54c"


def test_reconciliation_binds_effective_register_court_record() -> None:
    result = build_architecture_reconciliation(str(ROOT))
    assert result["source_register_merge_commit"] == SOURCE_REGISTER_MERGE_COMMIT
    assert result["source_register_virtual_bundle_id"] == SOURCE_REGISTER_VIRTUAL_BUNDLE_ID
    assert result["decision_traceability_count"] == 431
    assert result["architecture_reconciliation_disposition"] == DISPOSITION
    assert result["authority_effect"] == AUTHORITY_EFFECT


def test_reconciliation_requires_no_forward_repository_change() -> None:
    result = build_architecture_reconciliation(str(ROOT))
    assert result["forward_inheritance_entry_count"] == 0
    assert result["admitted_negative_knowledge_entry_count"] == 0
    assert result["supersession_edge_count"] == 0
    assert result["non_empty_destination_binding_count"] == 0
    assert result["architecture_effect_record_count"] == 431
    assert result["actionable_architecture_effect_count"] == 0
    assert result["architecture_execution_count"] == 0
    assert set(result["required_repository_changes"].values()) == {False}
    assert result["conformance_plan_mode"] == "PRESERVATION_ONLY_NO_FORWARD_ACCESSION_IMPLEMENTATION"


def test_reconciliation_preserves_reproducibility_gaps_without_expanding_them() -> None:
    result = build_architecture_reconciliation(str(ROOT))
    assert result["reproducibility_gap_count"] >= 2
    assert result["reproducibility_gap_count"] == len(result["reproducibility_gap_subject_ids"])
    assert len(result["reproducibility_gap_subject_ids"]) == len(set(result["reproducibility_gap_subject_ids"]))
    assert "PRESERVE_EXPLICIT_REPRODUCIBILITY_SOURCE_BINDING_GAPS_FOR_SUCCESSOR_REENTRY" in result["preservation_requirements"]


def test_reconciliation_does_not_resume_science_or_activate_downstream_capability() -> None:
    result = build_architecture_reconciliation(str(ROOT))
    assert result["next_operator_gate"] == "LSIAC-SCIENCE-RESUME"
    assert result["required_repository_changes"]["deferred_capability_activation"] is False
    assert result["required_repository_changes"]["validation_consumption_change"] is False
    assert result["required_repository_changes"]["semantic_or_ontology_change"] is False


def test_reconciliation_identity_is_deterministic_and_algorithm_bound() -> None:
    first = build_architecture_reconciliation(str(ROOT))
    second = build_architecture_reconciliation(str(ROOT))
    assert first == second
    identity = build_reconciliation_identity(algorithm_git_blob_sha=ALGORITHM_BLOB_SHA)
    assert identity == "c0f2c41f27a392fd0417b73db5449ceae2f768750e61536565309b1dd5eb96c6"
    assert len(identity) == 64
    assert identity == build_reconciliation_identity(algorithm_git_blob_sha=ALGORITHM_BLOB_SHA)
    assert identity != build_reconciliation_identity(algorithm_git_blob_sha="0" * 40)

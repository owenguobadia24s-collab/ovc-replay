from __future__ import annotations

from pathlib import Path

from ovc.research_operations.lsiac.canon_conformance_plan_gen0002 import (
    AUTHORITY_EFFECT,
    BASELINE_MAIN,
    PLAN_IDENTITY,
    PLAN_MODE,
    build_canon_conformance_plan,
    build_plan_identity,
)

ROOT = Path(__file__).resolve().parents[3]


def test_plan_identity_is_deterministic_and_bound() -> None:
    assert build_plan_identity() == PLAN_IDENTITY
    assert build_plan_identity() == build_plan_identity()


def test_plan_binds_effective_no_forward_accession_court_record() -> None:
    result = build_canon_conformance_plan(str(ROOT))
    assert result["baseline_main"] == BASELINE_MAIN
    assert result["decision_traceability_count"] == 431
    assert result["forward_inheritance_entry_count"] == 0
    assert result["admitted_negative_knowledge_entry_count"] == 0
    assert result["supersession_edge_count"] == 0
    assert result["non_empty_destination_binding_count"] == 0
    assert result["architecture_effect_record_count"] == 431
    assert result["actionable_architecture_effect_count"] == 0
    assert result["architecture_execution_count"] == 0


def test_plan_is_preservation_only_and_requires_no_repository_change() -> None:
    result = build_canon_conformance_plan(str(ROOT))
    assert result["conformance_plan_mode"] == PLAN_MODE
    assert set(result["required_repository_changes"].values()) == {False}
    assert result["authority_effect"] == AUTHORITY_EFFECT
    assert "PRESERVE_CURRENT_ARCHITECTURE" in result["preservation_requirements"]


def test_plan_preserves_reproducibility_gaps_for_successor_reentry() -> None:
    result = build_canon_conformance_plan(str(ROOT))
    assert result["reproducibility_gap_count"] >= 2
    assert result["reproducibility_gap_count"] == len(result["reproducibility_gap_subject_ids"])
    assert len(result["reproducibility_gap_subject_ids"]) == len(set(result["reproducibility_gap_subject_ids"]))
    assert "PRESERVE_EXPLICIT_REPRODUCIBILITY_SOURCE_BINDING_GAPS_FOR_SUCCESSOR_REENTRY" in result["preservation_requirements"]


def test_plan_stops_at_operator_reserved_science_resume() -> None:
    result = build_canon_conformance_plan(str(ROOT))
    assert result["terminal_state"] == "PRESERVATION_CONFORMANT_SCIENCE_RESUME_GATE_READY"
    assert result["next_packet"] == "LSIAC-SCIENCE-RESUME-READINESS"
    assert result["next_operator_gate"] == "LSIAC-SCIENCE-RESUME"
    assert "PRESERVE_BOUNDED_SECTION_23_SCIENTIFIC_ARCHITECTURE_DEVELOPMENT_FREEZE_UNTIL_OPERATOR_DECISION" in result["preservation_requirements"]

from __future__ import annotations

import pytest

from ovc.research_orchestration.checkpoint import (
    CheckpointError,
    CheckpointLedger,
    OpaqueSubstageCheckpoint,
    StageCompletion,
    assert_fresh_resume_equivalent,
    build_resume_plan,
)
from ovc.research_orchestration.models import PipelineProfile, StageDependency, StageSpec
from ovc.research_orchestration.planner import build_plan
from ovc.research_orchestration.registry import build_registry_snapshot


def stage(stage_id: str, *, deps=()) -> StageSpec:
    return StageSpec(
        stage_id=stage_id,
        stage_version="0.1",
        stage_kind="FIXTURE",
        implementation_identity=f"impl:{stage_id}",
        contract_identity=f"contract:{stage_id}",
        schema_identity=f"schema:{stage_id}",
        input_types=(),
        output_types=(f"{stage_id}_OUT",),
        dependencies=tuple(deps),
        checkpoint_capability="STAGE",
    )


def chain():
    a = stage("A")
    b = stage("B", deps=(StageDependency("A", "REQUIRED", ("A_OUT",)),))
    c = stage("C", deps=(StageDependency("B", "REQUIRED", ("B_OUT",)),))
    profile = PipelineProfile("P", "0.1", ("A", "B", "C"))
    plan = build_plan(snapshot=build_registry_snapshot(stage_specs=(a, b, c), profiles=(profile,)), profile_id="P")
    hashes = {item.stage_id: item.logical_hash for item in (a, b, c)}
    return plan, hashes


def completion(stage_id: str, spec_hash: str, *, output=None, content=None, attempt="ATTEMPT.1") -> StageCompletion:
    return StageCompletion(
        stage_id=stage_id,
        stage_spec_hash=spec_hash,
        output_logical_hash=output or f"logical:{stage_id}",
        content_hash=content or f"content:{stage_id}",
        attempt_id=attempt,
    )


def test_all_verified_complete_stages_are_reusable() -> None:
    plan, hashes = chain()
    completions = tuple(completion(s, hashes[s]) for s in plan.ordered_stage_ids)
    resume = build_resume_plan(
        plan=plan,
        semantic_run_id="RUN.1",
        completions=completions,
        expected_stage_spec_hashes=hashes,
        observed_content_hashes={s: f"content:{s}" for s in plan.ordered_stage_ids},
        new_attempt_id="ATTEMPT.2",
    )
    assert resume.semantic_run_id == "RUN.1"
    assert resume.reusable_completed_stage_ids == ("A", "B", "C")
    assert resume.rerun_stage_ids == ()


def test_missing_middle_stage_reruns_it_and_descendants_only() -> None:
    plan, hashes = chain()
    completions = (completion("A", hashes["A"]), completion("C", hashes["C"]))
    resume = build_resume_plan(
        plan=plan,
        semantic_run_id="RUN.1",
        completions=completions,
        expected_stage_spec_hashes=hashes,
        observed_content_hashes={"A": "content:A", "C": "content:C"},
        new_attempt_id="ATTEMPT.2",
    )
    assert resume.reusable_completed_stage_ids == ("A",)
    assert resume.rerun_stage_ids == ("B", "C")


def test_corrupt_stage_quarantines_and_reruns_descendants() -> None:
    plan, hashes = chain()
    completions = tuple(completion(s, hashes[s]) for s in plan.ordered_stage_ids)
    resume = build_resume_plan(
        plan=plan,
        semantic_run_id="RUN.1",
        completions=completions,
        expected_stage_spec_hashes=hashes,
        observed_content_hashes={"A": "content:A", "B": "CORRUPT", "C": "content:C"},
        new_attempt_id="ATTEMPT.2",
    )
    assert resume.quarantined_stage_ids == ("B",)
    assert resume.reusable_completed_stage_ids == ("A",)
    assert resume.rerun_stage_ids == ("B", "C")
    assert "IROF_CHECKPOINT_CONTENT_CORRUPTION" in resume.reason_codes


def test_changed_stage_spec_prevents_reuse_and_reruns_descendants() -> None:
    plan, hashes = chain()
    completions = tuple(completion(s, hashes[s]) for s in plan.ordered_stage_ids)
    changed = dict(hashes)
    changed["B"] = "new-spec-hash"
    resume = build_resume_plan(
        plan=plan,
        semantic_run_id="RUN.1",
        completions=completions,
        expected_stage_spec_hashes=changed,
        observed_content_hashes=None,
        new_attempt_id="ATTEMPT.2",
    )
    assert resume.reusable_completed_stage_ids == ("A",)
    assert resume.rerun_stage_ids == ("B", "C")


def test_incomplete_cannot_be_called_complete() -> None:
    with pytest.raises(CheckpointError, match="IROF_CHECKPOINT_INCOMPLETE_AS_COMPLETE"):
        StageCompletion("A", "spec", "logical", "content", "ATTEMPT.1", status="RUNNING")


def test_conflicting_completion_hash_quarantines() -> None:
    ledger = CheckpointLedger("RUN.1")
    ledger.register_completion(completion("A", "spec", content="one"))
    with pytest.raises(CheckpointError, match="IROF_CHECKPOINT_COMPLETION_HASH_CONFLICT"):
        ledger.register_completion(completion("A", "spec", content="two", attempt="ATTEMPT.2"))
    assert ledger.quarantined_stages["A"] == "IROF_CHECKPOINT_COMPLETION_HASH_CONFLICT"


def test_opaque_checkpoint_is_preserved_as_reference_only() -> None:
    checkpoint = OpaqueSubstageCheckpoint(
        checkpoint_id="CP.1",
        semantic_run_id="RUN.1",
        stage_id="B",
        owner_checkpoint_schema="owner://schema/v1",
        opaque_ref="external://opaque/checkpoint",
        content_hash="opaque-hash",
        attempt_id="ATTEMPT.1",
    )
    record = checkpoint.to_checkpoint_record()
    assert record.level == "OPAQUE_SUBSTAGE"
    assert record.opaque_ref == "external://opaque/checkpoint"
    assert record.owner_checkpoint_schema == "owner://schema/v1"


def test_corrupt_opaque_checkpoint_reruns_owner_stage_and_descendants() -> None:
    plan, hashes = chain()
    completions = tuple(completion(s, hashes[s]) for s in plan.ordered_stage_ids)
    opaque = OpaqueSubstageCheckpoint("CP.B", "RUN.1", "B", "owner:v1", "opaque://b", "opaque-good", "ATTEMPT.1")
    resume = build_resume_plan(
        plan=plan,
        semantic_run_id="RUN.1",
        completions=completions,
        expected_stage_spec_hashes=hashes,
        observed_content_hashes=None,
        new_attempt_id="ATTEMPT.2",
        opaque_checkpoints=(opaque,),
        observed_opaque_content_hashes={"CP.B": "opaque-corrupt"},
    )
    assert resume.quarantined_checkpoint_ids == ("CP.B",)
    assert resume.reusable_completed_stage_ids == ("A",)
    assert resume.rerun_stage_ids == ("B", "C")


def test_fresh_repeated_and_resumed_scientific_hashes_must_match() -> None:
    assert_fresh_resume_equivalent("same", "same", "same")
    with pytest.raises(CheckpointError, match="IROF_RESUME_SCIENTIFIC_HASH_MISMATCH"):
        assert_fresh_resume_equivalent("fresh", "fresh", "different")


def test_attempt_identity_is_not_stage_completion_semantic_identity() -> None:
    first = completion("A", "spec", attempt="ATTEMPT.1")
    second = completion("A", "spec", attempt="ATTEMPT.2")
    assert first.semantic_dict() == second.semantic_dict()

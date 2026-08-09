from __future__ import annotations

from pathlib import Path

import pytest

from ovc.research_operations.paths import ApprovedPathRegistry, ApprovedRoot
from ovc.research_operations.qa import QAAssertion, required_fields_check
from ovc.research_orchestration.evidence import (
    EvidenceError,
    artifact_declaration,
    assert_large_artifact_external,
    classify_scientific_result,
    incident_from_failure,
    project_research_read_model,
    run_qa_non_mutating,
    verify_artifacts,
)
from ovc.research_orchestration.models import (
    ArtifactRef,
    IntegratedRunReceipt,
    PipelineProfile,
    RunFailure,
    StageExecutionReceipt,
    StageSpec,
)
from ovc.research_orchestration.planner import build_plan
from ovc.research_orchestration.registry import build_registry_snapshot
from ovc.research_orchestration.telemetry import MetricValue, TelemetryReceipt
from ovc.research_operations.catalogue import ArtifactCatalogueBuilder


def simple_plan():
    stage = StageSpec(
        stage_id="A",
        stage_version="0.1",
        stage_kind="FIXTURE",
        implementation_identity="impl:A",
        contract_identity="contract:A",
        schema_identity="schema:A",
        input_types=(),
        output_types=("A_OUT",),
    )
    profile = PipelineProfile("P", "0.1", ("A",), ("A_OUT",))
    snapshot = build_registry_snapshot(stage_specs=(stage,), profiles=(profile,))
    return build_plan(snapshot=snapshot, profile_id="P")


def stage_receipt(*, status="COMPLETE", reasons=()) -> StageExecutionReceipt:
    return StageExecutionReceipt(
        run_id="RUN.1",
        attempt_id="ATTEMPT.1",
        stage_id="A",
        stage_version="0.1",
        status=status,
        input_hashes=(),
        output_artifact_ids=("ART.1",),
        metrics={"wall_seconds": 1.0},
        warnings=(),
        reason_codes=tuple(reasons),
    )


def run_receipt(receipt: StageExecutionReceipt | None = None) -> IntegratedRunReceipt:
    sr = receipt or stage_receipt()
    return IntegratedRunReceipt(
        run_id="RUN.1",
        attempt_id="ATTEMPT.1",
        status=sr.status,
        stage_receipts=(sr,),
        artifact_ids=("ART.1",),
        aggregate_metrics={"wall_seconds": 1.0},
    )


def local_artifact(cache_path: str, sha256: str, size: int) -> ArtifactRef:
    return ArtifactRef(
        artifact_id="ART.1",
        logical_hash="logical-1",
        artifact_type="FIXTURE",
        owner_stage_id="A",
        owner_run_id="RUN.1",
        lifecycle_state="COMPLETE",
        content_sha256=sha256,
        size_bytes=size,
        locations=({"root_alias": "TEST", "relative_path": cache_path},),
        verification_status="NOT_EVALUATED",
    )


def test_artifact_catalogue_reverifies_local_hash(tmp_path: Path) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"irof-evidence")
    import hashlib
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    registry = ApprovedPathRegistry((ApprovedRoot("TEST", tmp_path, read_only=True, required=True),))
    builder = ArtifactCatalogueBuilder(registry)
    catalogue = verify_artifacts(
        (local_artifact("artifact.bin", digest, path.stat().st_size),),
        builder=builder,
        generated_at="2026-08-09T10:00:00Z",
        source_commit="COMMIT",
    )
    assert catalogue.nodes[0].availability == "LOCAL_VERIFIED"
    assert catalogue.nodes[0].sha256 == digest
    assert catalogue.issues == ()


def test_hash_mismatch_is_blocking_catalogue_issue(tmp_path: Path) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"actual")
    registry = ApprovedPathRegistry((ApprovedRoot("TEST", tmp_path, read_only=True, required=True),))
    catalogue = verify_artifacts(
        (local_artifact("artifact.bin", "0" * 64, len(b"actual")),),
        builder=ArtifactCatalogueBuilder(registry),
        generated_at="2026-08-09T10:00:00Z",
        source_commit="COMMIT",
    )
    assert any(issue.code == "HASH_MISMATCH" and issue.severity == "BLOCK" for issue in catalogue.issues)


def test_unportable_local_location_fails_closed() -> None:
    artifact = ArtifactRef(
        artifact_id="ART.BAD",
        logical_hash="logical",
        artifact_type="FIXTURE",
        owner_stage_id="A",
        owner_run_id="RUN.1",
        lifecycle_state="COMPLETE",
        locations=({"kind": "LOCAL", "value": "/absolute/path"},),
    )
    with pytest.raises(EvidenceError, match="IROF_EVIDENCE_LOCATION_NOT_PORTABLE"):
        artifact_declaration(artifact)


def test_remote_r2_declaration_preserves_external_location() -> None:
    artifact = ArtifactRef(
        artifact_id="ART.R2",
        logical_hash="logical",
        artifact_type="FIXTURE",
        owner_stage_id="A",
        owner_run_id="RUN.1",
        lifecycle_state="COMPLETE",
        locations=({"kind": "R2", "value": "r2://ovc-evidence/object"},),
        verification_status="REMOTE_VERIFIED",
    )
    declaration = artifact_declaration(artifact)
    assert declaration["source_kind"] == "R2"
    assert declaration["availability"] == "REMOTE_VERIFIED"


def test_existing_qa_runner_cannot_mutate_target() -> None:
    target = {"record_id": "R", "required": "present"}
    before = dict(target)
    run = run_qa_non_mutating(
        target,
        checks=(required_fields_check("REQ", ("required",)),),
        target_id="R",
        source_commit="COMMIT",
    )
    assert run.disposition == "PASS"
    assert target == before


def test_mutating_qa_check_is_rejected() -> None:
    target = {"record_id": "R", "value": 1}

    def bad_check(value):
        value["value"] = 2
        return QAAssertion("BAD", "R", "PASS", "BLOCK", "bad")

    with pytest.raises(RuntimeError, match="QA checks mutated their target"):
        run_qa_non_mutating(target, checks=(bad_check,), target_id="R", source_commit="COMMIT")


def test_same_run_evidence_rebuilds_to_same_read_model_hash() -> None:
    plan = simple_plan()
    receipt = run_receipt()
    telemetry = TelemetryReceipt(
        run_id="RUN.1",
        stage_id="A",
        metrics=(MetricValue("wall_seconds", 1.0, "seconds"),),
    )
    first = project_research_read_model(
        source_commit="COMMIT",
        catalogue=None,
        run_receipt=receipt,
        plan=plan,
        telemetry=(telemetry,),
    )
    second = project_research_read_model(
        source_commit="COMMIT",
        catalogue=None,
        run_receipt=receipt,
        plan=plan,
        telemetry=(telemetry,),
    )
    assert first.logical_sha256 == second.logical_sha256
    run_node = next(node for node in first.nodes if node.object_type == "IROF_INTEGRATED_RUN_RECEIPT")
    assert run_node.payload["lineage"]["dag"]["ordered_stage_ids"] == ["A"]
    assert run_node.payload["lineage"]["stage_statuses"] == {"A": "COMPLETE"}
    assert run_node.payload["lineage"]["telemetry"]["A"]["scientific_effect"] == "NONE"


def test_failure_incident_has_no_market_claim_effect() -> None:
    failure = RunFailure(
        run_id="RUN.1",
        failure_class="AUTHORITY",
        reason_code="IROF_OWNER_AUTHORITY_BINDING_MISSING",
        blocked_stage_id="A",
        detail="owner authority absent",
    )
    incident = incident_from_failure(failure)
    assert incident.market_claim_effect == "NONE"
    assert incident.to_record()["authority_state"] == "DERIVED_EXECUTION_EVIDENCE_ONLY"


@pytest.mark.parametrize("status", ["NO_STABLE_FAMILY", "NULL_RESULT", "NOT_ESTABLISHED", "NOT_EVALUABLE", "UNRESOLVED", "ZERO_FAMILY", "RESIDUAL_ONLY"])
def test_negative_or_null_scientific_result_is_not_incident(status: str) -> None:
    assert classify_scientific_result(status) == "SCIENTIFIC_RESULT_NOT_INCIDENT"


def test_large_git_local_artifact_is_rejected_but_external_is_allowed() -> None:
    local = ArtifactRef(
        artifact_id="ART.LARGE",
        logical_hash="logical",
        artifact_type="RAW_TELEMETRY",
        owner_stage_id="A",
        owner_run_id="RUN.1",
        lifecycle_state="COMPLETE",
        size_bytes=20 * 1024 * 1024,
        locations=({"root_alias": "GIT", "relative_path": "large.bin"},),
    )
    with pytest.raises(EvidenceError, match="IROF_EVIDENCE_LARGE_ARTIFACT_MUST_BE_EXTERNAL"):
        assert_large_artifact_external(local)
    remote = ArtifactRef(
        artifact_id="ART.LARGE.R2",
        logical_hash="logical",
        artifact_type="RAW_TELEMETRY",
        owner_stage_id="A",
        owner_run_id="RUN.1",
        lifecycle_state="COMPLETE",
        size_bytes=20 * 1024 * 1024,
        locations=({"kind": "R2", "value": "r2://bucket/raw"},),
    )
    assert_large_artifact_external(remote)

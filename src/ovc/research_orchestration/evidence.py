from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from ovc.research_operations.catalogue import ArtifactCatalogue, ArtifactCatalogueBuilder
from ovc.research_operations.qa import Check, QARun, QARunner
from ovc.research_operations.read_model import ReadModelBuilder, ResearchReadModel

from .models import ArtifactRef, IntegratedRunReceipt, RunFailure, StageExecutionReceipt
from .planner import CanonicalPlan
from .telemetry import TelemetryReceipt


class EvidenceError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


SCIENTIFIC_NULL_STATUSES = frozenset({
    "NO_STABLE_FAMILY",
    "NULL_RESULT",
    "METHOD_DEPENDENT_STRUCTURE_ONLY",
    "NOT_ESTABLISHED",
    "NOT_EVALUABLE",
    "UNRESOLVED",
    "ZERO_FAMILY",
    "RESIDUAL_ONLY",
})
INCIDENT_FAILURE_CLASSES = frozenset({"AUTHORITY", "DEPENDENCY", "EXECUTION"})


@dataclass(frozen=True)
class IncidentProjection:
    incident_id: str
    run_id: str
    category: str
    reason_code: str
    stage_id: str | None
    detail: str | None
    market_claim_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.market_claim_effect != "NONE":
            raise EvidenceError("IROF_EVIDENCE_INCIDENT_MARKET_CLAIM_FORBIDDEN", self.incident_id)

    def to_record(self) -> dict[str, Any]:
        return {
            "record_id": self.incident_id,
            "record_type": "IROF_EXECUTION_INCIDENT",
            "authority_state": "DERIVED_EXECUTION_EVIDENCE_ONLY",
            "lifecycle_state": "FROZEN",
            "source_release_refs": [],
            "reproducibility_state": "SOURCE_BOUND",
            "missingness": [],
            "lineage": {
                "run_id": self.run_id,
                "stage_id": self.stage_id,
                "category": self.category,
                "reason_code": self.reason_code,
                "detail": self.detail,
                "market_claim_effect": self.market_claim_effect,
            },
        }


def artifact_declaration(artifact: ArtifactRef) -> dict[str, Any]:
    if not artifact.locations:
        raise EvidenceError("IROF_EVIDENCE_ARTIFACT_LOCATION_REQUIRED", artifact.artifact_id)

    portable_local = next(
        (
            dict(item)
            for item in artifact.locations
            if "root_alias" in item and "relative_path" in item
        ),
        None,
    )
    remote_kind: str | None = None
    if portable_local is not None:
        source_kind = "LOCAL"
        location = portable_local
        locations: list[dict[str, str]] = []
        availability = "NOT_EVALUATED"
    else:
        remote_locations: list[dict[str, str]] = []
        for item in artifact.locations:
            kind = str(item.get("kind", "")).upper()
            if kind in {"R2", "GITHUB_ACTIONS"}:
                remote_kind = kind
                remote_locations.append(dict(item))
        if remote_kind is None or not remote_locations:
            raise EvidenceError("IROF_EVIDENCE_LOCATION_NOT_PORTABLE", artifact.artifact_id)
        if len({str(item.get("kind", "")).upper() for item in remote_locations}) != 1:
            raise EvidenceError("IROF_EVIDENCE_MIXED_REMOTE_LOCATION_KINDS", artifact.artifact_id)
        source_kind = remote_kind
        location = None
        locations = remote_locations
        availability = artifact.verification_status if artifact.verification_status in {
            "NOT_EVALUATED", "REMOTE_PRESENT", "REMOTE_VERIFIED", "PARTIALLY_AVAILABLE",
            "MISSING", "EXPIRED", "QUARANTINED",
        } else "NOT_EVALUATED"

    declaration: dict[str, Any] = {
        "artifact_id": artifact.artifact_id,
        "artifact_type": artifact.artifact_type,
        "owner": artifact.owner_stage_id,
        "authority": artifact.authority_classification,
        "release_id": artifact.owner_run_id,
        "sha256": artifact.content_sha256,
        "size_bytes": artifact.size_bytes,
        "media_type": artifact.media_type,
        "dependencies": list(artifact.parent_artifact_ids),
        "source_kind": source_kind,
        "availability": availability,
        "metadata": {
            "logical_hash": artifact.logical_hash,
            "semantic_cache_key": artifact.semantic_cache_key,
            "schema_identity": artifact.schema_identity,
            "lifecycle_state": artifact.lifecycle_state,
            "verification_status": artifact.verification_status,
        },
    }
    if location is not None:
        declaration["location"] = location
    else:
        declaration["locations"] = locations
    return declaration


def verify_artifacts(
    artifacts: Iterable[ArtifactRef],
    *,
    builder: ArtifactCatalogueBuilder,
    generated_at: str,
    source_commit: str,
) -> ArtifactCatalogue:
    declarations = [artifact_declaration(item) for item in artifacts]
    return builder.verify_declarations(declarations, generated_at=generated_at, source_commit=source_commit)


def stage_receipt_record(receipt: StageExecutionReceipt, *, artifact_refs: Iterable[str] = ()) -> dict[str, Any]:
    return {
        "record_id": f"IROF.STAGE.RECEIPT.{receipt.run_id}.{receipt.stage_id}",
        "record_type": "IROF_STAGE_EXECUTION_RECEIPT",
        "authority_state": "DERIVED_EXECUTION_EVIDENCE_ONLY",
        "lifecycle_state": "FROZEN",
        "source_release_refs": list(artifact_refs),
        "reproducibility_state": "RECEIPT_ONLY",
        "missingness": [],
        "lineage": {
            "run_id": receipt.run_id,
            "stage_id": receipt.stage_id,
            "stage_version": receipt.stage_version,
            "status": receipt.status,
            "input_hashes": list(receipt.input_hashes),
            "output_artifact_ids": list(receipt.output_artifact_ids),
            "reason_codes": list(receipt.reason_codes),
            "metrics": dict(receipt.metrics),
            "warnings": list(receipt.warnings),
            "attempt_id": receipt.attempt_id,
        },
    }


def run_receipt_record(
    receipt: IntegratedRunReceipt,
    *,
    plan: CanonicalPlan,
    telemetry: Iterable[TelemetryReceipt] = (),
) -> dict[str, Any]:
    telemetry_by_stage = {
        item.stage_id: item.to_dict()
        for item in sorted(telemetry, key=lambda item: item.stage_id)
    }
    return {
        "record_id": f"IROF.RUN.RECEIPT.{receipt.run_id}",
        "record_type": "IROF_INTEGRATED_RUN_RECEIPT",
        "authority_state": "DERIVED_EXECUTION_EVIDENCE_ONLY",
        "lifecycle_state": "FROZEN",
        "source_release_refs": list(receipt.artifact_ids),
        "reproducibility_state": "SOURCE_BOUND",
        "missingness": [],
        "lineage": {
            "run_id": receipt.run_id,
            "status": receipt.status,
            "logical_hash": receipt.logical_hash,
            "qa_manifest_id": receipt.qa_manifest_id,
            "dag": {
                "profile_id": plan.profile_id,
                "profile_hash": plan.profile_hash,
                "dag_hash": plan.dag.logical_hash,
                "ordered_stage_ids": list(plan.ordered_stage_ids),
                "edges": [list(edge) for edge in plan.dag.edges],
            },
            "stage_statuses": {
                item.stage_id: item.status
                for item in sorted(receipt.stage_receipts, key=lambda item: item.stage_id)
            },
            "telemetry": telemetry_by_stage,
            "aggregate_metrics": dict(receipt.aggregate_metrics),
            "attempt_id": receipt.attempt_id,
        },
    }


def run_qa_non_mutating(
    target: dict[str, Any],
    *,
    checks: Iterable[Check],
    target_id: str,
    source_commit: str,
) -> QARun:
    return QARunner(checks).run(target, target_id=target_id, source_commit=source_commit)


def project_research_read_model(
    *,
    source_commit: str,
    catalogue: ArtifactCatalogue | None,
    run_receipt: IntegratedRunReceipt,
    plan: CanonicalPlan,
    telemetry: Iterable[TelemetryReceipt] = (),
    qa_runs: Iterable[QARun] = (),
    incidents: Iterable[IncidentProjection] = (),
) -> ResearchReadModel:
    records: list[dict[str, Any]] = [
        run_receipt_record(run_receipt, plan=plan, telemetry=telemetry),
    ]
    records.extend(stage_receipt_record(item, artifact_refs=item.output_artifact_ids) for item in run_receipt.stage_receipts)
    records.extend(item.to_record() for item in incidents)
    return ReadModelBuilder().build(
        source_commit=source_commit,
        catalogue=catalogue,
        records=records,
        qa_runs=(item.to_dict() for item in qa_runs),
    )


def incident_from_failure(failure: RunFailure) -> IncidentProjection:
    if failure.failure_class not in INCIDENT_FAILURE_CLASSES:
        raise EvidenceError("IROF_EVIDENCE_FAILURE_CLASS_NOT_INCIDENT", failure.failure_class)
    return IncidentProjection(
        incident_id=f"IROF.INCIDENT.{failure.run_id}.{failure.reason_code}",
        run_id=failure.run_id,
        category=failure.failure_class,
        reason_code=failure.reason_code,
        stage_id=failure.blocked_stage_id,
        detail=failure.detail,
    )


def classify_scientific_result(status: str) -> str:
    normalized = str(status).upper()
    if normalized in SCIENTIFIC_NULL_STATUSES:
        return "SCIENTIFIC_RESULT_NOT_INCIDENT"
    return "SCIENTIFIC_RESULT"


def assert_large_artifact_external(artifact: ArtifactRef, *, git_size_limit_bytes: int = 10 * 1024 * 1024) -> None:
    if artifact.size_bytes is None or artifact.size_bytes <= git_size_limit_bytes:
        return
    if any(str(location.get("kind", "")).upper() in {"R2", "EXTERNAL", "EXTERNAL_ARTIFACT_ROOT"} for location in artifact.locations):
        return
    raise EvidenceError("IROF_EVIDENCE_LARGE_ARTIFACT_MUST_BE_EXTERNAL", artifact.artifact_id)

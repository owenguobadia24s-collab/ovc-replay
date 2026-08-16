from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_routing import VIT_MANDATORY, validate_vit_lineage_record

BASE_INDEPENDENT = "BASE_INDEPENDENT"
BASE_SENSITIVE = "BASE_SENSITIVE"
READY = "READY"
WAIT = "WAIT"
BLOCKED = "BLOCKED"
QUARANTINED = "QUARANTINED"
OPERATOR_REQUIRED = "OPERATOR_REQUIRED"
REQUEUE = "REQUEUE"
INTEGRATED = "INTEGRATED"

PARALLEL_DEVELOPMENT = True
PARALLEL_MERGE = False
FINAL_INTEGRATION_LEASE_COUNT = 1
FORCE_PUSH = False
HISTORY_REWRITE = False

LEASE_TARGET_SECONDS = 300
LEASE_WARNING_SECONDS = 600
LEASE_RELEASE_REQUEUE_SECONDS = 900

BASE_INDEPENDENT_CHECKS = frozenset({
    "PACKET_LOCAL_TESTS",
    "SCHEMA_FIXTURE_VALIDATION",
    "BOUND_IMMUTABLE_EVIDENCE",
    "CANDIDATE_CORRECTNESS_ASSURANCE",
    "QA_EVIDENCE_GENERATION",
})
BASE_SENSITIVE_CHECKS = frozenset({
    "CURRENT_MAIN_RECONCILIATION",
    "PDC_HEAD_MOVEMENT_CLASSIFICATION",
    "AFFECTED_DEPENDENCY_CLOSURE",
    "EXACT_TREE_MERGE_READINESS",
    "MANDATORY_FINAL_HEAD_ASSURANCE",
    "IMMEDIATE_PREMERGE_HEAD_AND_BASE_PIN",
})
OPERATOR_GATE_CLASSES = frozenset({"OPERATOR_REQUIRED", "OPERATOR_GATE", "RESERVED"})


def _is_sha256(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value.lower() == value


@dataclass(frozen=True)
class QueueCandidate:
    packet_id: str
    plan_id: str
    candidate_head_sha: str
    baseline_main_sha: str
    ready_sequence: int
    queue_state: str = "BUILD"
    implementation_complete: bool = False
    qa_status: str = "PENDING"
    authority_delta: str = "NONE"
    gate_class: str = "AUTO_EXECUTABLE"
    operator_authority_satisfied: bool = False
    merge_authority_resolved: bool = False
    preliminary_assurance_pass: bool = False
    rollback_defined: bool = False
    dependency_footprint_pinned: bool = False
    blocking_reviews: tuple[str, ...] = ()
    blocking_issues: tuple[str, ...] = ()
    blocking_warnings: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    vit_pip_id: str = ""
    vit_generation_id: str = ""
    vit_placement_id: str = ""
    vit_lineage_ref: str = ""
    vit_lineage_record: Mapping[str, Any] | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "QueueCandidate":
        raw_lineage = value.get("vit_lineage_record")
        lineage = dict(raw_lineage) if isinstance(raw_lineage, Mapping) else None
        return cls(
            packet_id=str(value.get("packet_id", "")).strip(),
            plan_id=str(value.get("plan_id", "")).strip(),
            candidate_head_sha=str(value.get("candidate_head_sha", "")).strip(),
            baseline_main_sha=str(value.get("baseline_main_sha", "")).strip(),
            ready_sequence=int(value.get("ready_sequence", 0)),
            queue_state=str(value.get("queue_state", "BUILD")).upper(),
            implementation_complete=bool(value.get("implementation_complete", False)),
            qa_status=str(value.get("qa_status", "PENDING")).upper(),
            authority_delta=str(value.get("authority_delta", "NONE")).upper(),
            gate_class=str(value.get("gate_class", "AUTO_EXECUTABLE")).upper(),
            operator_authority_satisfied=bool(value.get("operator_authority_satisfied", False)),
            merge_authority_resolved=bool(value.get("merge_authority_resolved", False)),
            preliminary_assurance_pass=bool(value.get("preliminary_assurance_pass", False)),
            rollback_defined=bool(value.get("rollback_defined", False)),
            dependency_footprint_pinned=bool(value.get("dependency_footprint_pinned", False)),
            blocking_reviews=tuple(sorted(map(str, value.get("blocking_reviews", ())))),
            blocking_issues=tuple(sorted(map(str, value.get("blocking_issues", ())))),
            blocking_warnings=tuple(sorted(map(str, value.get("blocking_warnings", ())))),
            reason_codes=tuple(sorted(map(str, value.get("reason_codes", ())))),
            vit_pip_id=str(value.get("vit_pip_id", "")).strip(),
            vit_generation_id=str(value.get("vit_generation_id", "")).strip(),
            vit_placement_id=str(value.get("vit_placement_id", "")).strip(),
            vit_lineage_ref=str(value.get("vit_lineage_ref", "")).strip(),
            vit_lineage_record=lineage,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "plan_id": self.plan_id,
            "candidate_head_sha": self.candidate_head_sha,
            "baseline_main_sha": self.baseline_main_sha,
            "ready_sequence": self.ready_sequence,
            "queue_state": self.queue_state,
            "implementation_complete": self.implementation_complete,
            "qa_status": self.qa_status,
            "authority_delta": self.authority_delta,
            "gate_class": self.gate_class,
            "operator_authority_satisfied": self.operator_authority_satisfied,
            "merge_authority_resolved": self.merge_authority_resolved,
            "preliminary_assurance_pass": self.preliminary_assurance_pass,
            "rollback_defined": self.rollback_defined,
            "dependency_footprint_pinned": self.dependency_footprint_pinned,
            "blocking_reviews": list(self.blocking_reviews),
            "blocking_issues": list(self.blocking_issues),
            "blocking_warnings": list(self.blocking_warnings),
            "reason_codes": list(self.reason_codes),
            "vit_pip_id": self.vit_pip_id,
            "vit_generation_id": self.vit_generation_id,
            "vit_placement_id": self.vit_placement_id,
            "vit_lineage_ref": self.vit_lineage_ref,
            "vit_lineage_record": dict(self.vit_lineage_record) if self.vit_lineage_record is not None else None,
        }


@dataclass(frozen=True)
class QueueState:
    queue_id: str
    candidates: tuple[QueueCandidate, ...]
    lease_holder_packet_id: str | None = None
    lease_acquired_at: str | None = None
    generation: int = 0

    def as_dict(self) -> dict[str, Any]:
        head = queue_head(self)
        return {
            "schema": "ovc-serialized-integration-queue-state/v1",
            "queue_id": self.queue_id,
            "generation": self.generation,
            "candidates": [row.as_dict() for row in self.candidates],
            "ready_packet_ids": [row.packet_id for row in self.candidates if row.queue_state == READY],
            "queue_head_packet_id": head.packet_id if head else None,
            "lease_holder_packet_id": self.lease_holder_packet_id,
            "lease_acquired_at": self.lease_acquired_at,
            "final_integration_lease_count": 1 if self.lease_holder_packet_id else 0,
            "parallel_development": PARALLEL_DEVELOPMENT,
            "parallel_merge": PARALLEL_MERGE,
            "force_push": FORCE_PUSH,
            "history_rewrite": HISTORY_REWRITE,
            "authority_effect": "NONE",
        }


def classify_assurance(check_name: str) -> str:
    check = str(check_name).upper().strip()
    if check in BASE_INDEPENDENT_CHECKS:
        return BASE_INDEPENDENT
    if check in BASE_SENSITIVE_CHECKS:
        return BASE_SENSITIVE
    raise ValueError(f"unknown SIQ assurance check: {check_name!r}")


def _lineage_blockers(candidate: QueueCandidate) -> list[str]:
    if not (
        _is_sha256(candidate.vit_pip_id)
        and _is_sha256(candidate.vit_generation_id)
        and _is_sha256(candidate.vit_placement_id)
        and bool(candidate.vit_lineage_ref)
        and candidate.vit_lineage_record is not None
    ):
        return ["VIT_LINEAGE_REQUIRED"]
    try:
        validated = validate_vit_lineage_record(candidate.vit_lineage_record, lineage_ref=candidate.vit_lineage_ref)
    except (VitContractError, TypeError, ValueError):
        return ["VIT_LINEAGE_INVALID"]
    if validated.route_class != VIT_MANDATORY:
        return ["VIT_LINEAGE_ROUTE_NOT_MANDATORY"]
    if validated.packet_id != candidate.packet_id:
        return ["VIT_LINEAGE_PACKET_MISMATCH"]
    if (
        validated.pip_id != candidate.vit_pip_id
        or validated.generation_id != candidate.vit_generation_id
        or validated.placement_id != candidate.vit_placement_id
    ):
        return ["VIT_LINEAGE_ID_MISMATCH"]
    return []


def evaluate_ready_admission(value: Mapping[str, Any] | QueueCandidate) -> QueueCandidate:
    candidate = value if isinstance(value, QueueCandidate) else QueueCandidate.from_mapping(value)
    blockers = list(candidate.reason_codes)
    if candidate.queue_state == QUARANTINED:
        return replace(candidate, reason_codes=tuple(sorted(set(blockers + ["CANDIDATE_QUARANTINED"]))))
    if candidate.queue_state == BLOCKED:
        return replace(candidate, reason_codes=tuple(sorted(set(blockers + ["CANDIDATE_BLOCKED"]))))
    if not candidate.packet_id: blockers.append("PACKET_ID_MISSING")
    if not candidate.plan_id: blockers.append("PLAN_ID_MISSING")
    if len(candidate.candidate_head_sha) != 40: blockers.append("CANDIDATE_HEAD_SHA_INVALID")
    if len(candidate.baseline_main_sha) != 40: blockers.append("BASELINE_MAIN_SHA_INVALID")
    if candidate.ready_sequence <= 0: blockers.append("READY_SEQUENCE_INVALID")
    if not candidate.implementation_complete: blockers.append("IMPLEMENTATION_INCOMPLETE")
    if candidate.qa_status != "PASS": blockers.append("QA_NOT_PASS")
    if candidate.blocking_reviews: blockers.append("BLOCKING_REVIEW_PRESENT")
    if candidate.blocking_issues: blockers.append("BLOCKING_ISSUE_PRESENT")
    if candidate.blocking_warnings: blockers.append("BLOCKING_WARNING_PRESENT")
    if not candidate.preliminary_assurance_pass: blockers.append("PRELIMINARY_ASSURANCE_NOT_PASS")
    if not candidate.rollback_defined: blockers.append("ROLLBACK_NOT_DEFINED")
    if not candidate.dependency_footprint_pinned: blockers.append("DEPENDENCY_FOOTPRINT_NOT_PINNED")
    blockers.extend(_lineage_blockers(candidate))
    operator_boundary = candidate.gate_class in OPERATOR_GATE_CLASSES or candidate.authority_delta != "NONE"
    lineage_blocked = any(code.startswith("VIT_LINEAGE_") for code in blockers)
    if lineage_blocked:
        state = WAIT
    elif operator_boundary and not (candidate.operator_authority_satisfied and candidate.merge_authority_resolved):
        blockers.append("OPERATOR_AUTHORITY_REQUIRED")
        state = OPERATOR_REQUIRED
    elif blockers:
        state = WAIT
    else:
        state = READY
    return replace(candidate, queue_state=state, reason_codes=tuple(sorted(set(blockers))))


def build_queue_state(candidates: Sequence[Mapping[str, Any] | QueueCandidate], *, queue_id: str = "OVC.SIQ.v0.1", generation: int = 0) -> QueueState:
    admitted = [evaluate_ready_admission(row) for row in candidates]
    admitted.sort(key=lambda row: (row.ready_sequence, row.packet_id, row.candidate_head_sha))
    return QueueState(queue_id=queue_id, candidates=tuple(admitted), generation=generation)


def enqueue_candidate(state: QueueState, value: Mapping[str, Any] | QueueCandidate) -> QueueState:
    candidate = value if isinstance(value, QueueCandidate) else QueueCandidate.from_mapping(value)
    if any(row.packet_id == candidate.packet_id for row in state.candidates):
        raise ValueError(f"packet already materialized in SIQ: {candidate.packet_id}")
    if candidate.ready_sequence <= 0:
        candidate = replace(candidate, ready_sequence=max((row.ready_sequence for row in state.candidates), default=0) + 1)
    admitted = evaluate_ready_admission(candidate)
    candidates = tuple(sorted(state.candidates + (admitted,), key=lambda row: (row.ready_sequence, row.packet_id, row.candidate_head_sha)))
    return replace(state, candidates=candidates, generation=state.generation + 1)


def queue_head(state: QueueState) -> QueueCandidate | None:
    return next((row for row in state.candidates if row.queue_state == READY), None)


def acquire_final_integration_lease(state: QueueState, *, packet_id: str, assurance_class: str, acquired_at: str | None = None) -> QueueState:
    if assurance_class != BASE_SENSITIVE:
        raise PermissionError("BASE_INDEPENDENT work must not hold the SIQ final-integration lease")
    head = queue_head(state)
    if head is None or head.packet_id != str(packet_id):
        raise PermissionError("only the deterministic READY queue head may acquire the lease")
    if state.lease_holder_packet_id not in {None, str(packet_id)}:
        raise PermissionError("the SIQ final-integration lease already has a holder")
    timestamp = acquired_at or datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    return replace(state, lease_holder_packet_id=str(packet_id), lease_acquired_at=timestamp, generation=state.generation + 1)


def release_final_integration_lease(state: QueueState, *, packet_id: str) -> QueueState:
    if state.lease_holder_packet_id != str(packet_id):
        raise PermissionError("only the current SIQ lease holder may release the lease")
    return replace(state, lease_holder_packet_id=None, lease_acquired_at=None, generation=state.generation + 1)


def handle_lease_elapsed(state: QueueState, *, packet_id: str, elapsed_seconds: int, admitted_base_sensitive_check_active: bool) -> tuple[QueueState, dict[str, Any]]:
    if state.lease_holder_packet_id != str(packet_id):
        raise PermissionError("elapsed lease handling requires the current holder")
    if elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be non-negative")
    if elapsed_seconds > LEASE_RELEASE_REQUEUE_SECONDS and not admitted_base_sensitive_check_active:
        candidates = tuple(replace(row, queue_state=READY, reason_codes=tuple(sorted(set(row.reason_codes + ("LEASE_TIMEOUT_REQUEUED",))))) if row.packet_id == str(packet_id) else row for row in state.candidates)
        new_state = replace(state, candidates=candidates, lease_holder_packet_id=None, lease_acquired_at=None, generation=state.generation + 1)
        disposition = "RELEASE_AND_REQUEUE"
    elif elapsed_seconds > LEASE_WARNING_SECONDS:
        new_state = state
        disposition = "WARNING_ACTIVE_CHECK" if admitted_base_sensitive_check_active else "WARNING"
    else:
        new_state = state
        disposition = "WITHIN_BUDGET"
    return new_state, {"packet_id": str(packet_id), "elapsed_seconds": int(elapsed_seconds), "disposition": disposition, "authority_effect": "NONE"}


def terminate_lease(state: QueueState, *, packet_id: str, disposition: str, reason_code: str) -> QueueState:
    target = str(disposition).upper()
    if target not in {REQUEUE, BLOCKED, QUARANTINED, OPERATOR_REQUIRED}:
        raise ValueError("lease termination disposition must fail closed")
    if state.lease_holder_packet_id != str(packet_id):
        raise PermissionError("lease termination requires the current holder")
    candidates = tuple(replace(row, queue_state=READY if target == REQUEUE else target, reason_codes=tuple(sorted(set(row.reason_codes + (str(reason_code),))))) if row.packet_id == str(packet_id) else row for row in state.candidates)
    return replace(state, candidates=candidates, lease_holder_packet_id=None, lease_acquired_at=None, generation=state.generation + 1)


def mark_integrated(state: QueueState, *, packet_id: str, merge_sha: str) -> QueueState:
    if state.lease_holder_packet_id != str(packet_id):
        raise PermissionError("integration completion requires the current SIQ lease holder")
    if len(str(merge_sha)) != 40:
        raise ValueError("merge_sha must be a 40-character git SHA")
    candidates = tuple(replace(row, queue_state=INTEGRATED, reason_codes=tuple(sorted(set(row.reason_codes + (f"MERGE_SHA:{merge_sha}",))))) if row.packet_id == str(packet_id) else row for row in state.candidates)
    return replace(state, candidates=candidates, lease_holder_packet_id=None, lease_acquired_at=None, generation=state.generation + 1)

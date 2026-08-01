"""Deterministic dry-run closure and merge-receipt comparison services."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .identity import canonical_sha256, normalize_relative_path


class ClosureError(ValueError):
    """Raised for invalid closure policy or snapshot inputs."""


_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class WorkflowResult:
    name: str
    run_id: int
    result: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "run_id": self.run_id, "result": self.result}


@dataclass(frozen=True)
class ClosurePolicy:
    policy_id: str
    programme_id: str
    base_branch: str
    merge_method: str
    exact_head_required: bool
    allowed_head_patterns: tuple[str, ...]
    allowed_path_patterns: tuple[str, ...]
    required_qa_status: str
    required_decision: str
    required_reserved_authority_delta: str
    zero_warning_required: bool
    zero_unresolved_review_required: bool
    repository_bot_write: str
    direct_main_write: str
    force_push: str
    history_rewrite: str
    policy_hash: str


@dataclass(frozen=True)
class ClosureSnapshot:
    policy_id: str
    policy_hash: str
    plan_id: str
    plan_version: str
    programme_id: str
    packet_id: str
    gate_id: str
    pull_request: int
    base_branch: str
    baseline_commit: str
    head_branch: str
    head_sha: str
    changed_files: tuple[str, ...]
    required_checks: tuple[WorkflowResult, ...]
    qa_status: str
    decision: str
    decision_id: str
    authority_delta: str
    reserved_authority_delta: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    unresolved_review_count: int
    rollback: str
    next_packet: str

    @property
    def snapshot_id(self) -> str:
        return canonical_sha256(self.to_dict(), role="CLOSURE_SNAPSHOT")

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_hash": self.policy_hash,
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "programme_id": self.programme_id,
            "packet_id": self.packet_id,
            "gate_id": self.gate_id,
            "pull_request": self.pull_request,
            "base_branch": self.base_branch,
            "baseline_commit": self.baseline_commit,
            "head_branch": self.head_branch,
            "head_sha": self.head_sha,
            "changed_files": list(self.changed_files),
            "required_checks": [row.to_dict() for row in self.required_checks],
            "qa_status": self.qa_status,
            "decision": self.decision,
            "decision_id": self.decision_id,
            "authority_delta": self.authority_delta,
            "reserved_authority_delta": self.reserved_authority_delta,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "unresolved_review_count": self.unresolved_review_count,
            "rollback": self.rollback,
            "next_packet": self.next_packet,
        }


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClosureError(f"{field} must be a non-empty string")
    return value


def _string_tuple(value: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ClosureError(f"{field} must be a {'possibly empty ' if allow_empty else 'non-empty '}list")
    result = tuple(_string(item, field) for item in value)
    if len(result) != len(set(result)):
        raise ClosureError(f"{field} contains duplicates")
    return result


def parse_closure_policy(obj: Mapping[str, Any]) -> ClosurePolicy:
    expected = {
        "schema", "policy_id", "programme_id", "base_branch", "merge_method",
        "exact_head_required", "allowed_head_patterns", "allowed_path_patterns",
        "required_qa_status", "required_decision", "required_reserved_authority_delta",
        "zero_warning_required", "zero_unresolved_review_required", "repository_bot_write",
        "direct_main_write", "force_push", "history_rewrite",
    }
    if set(obj) != expected:
        raise ClosureError(f"closure policy fields mismatch: {sorted(set(obj) ^ expected)}")
    if obj.get("schema") != "ovc-closure-policy/v1":
        raise ClosureError("unsupported closure policy schema")
    if obj.get("base_branch") != "main" or obj.get("merge_method") != "squash":
        raise ClosureError("closure policy must target main through squash")
    if obj.get("exact_head_required") is not True:
        raise ClosureError("exact head pinning is required")
    if obj.get("required_reserved_authority_delta") != "NONE":
        raise ClosureError("closure policy cannot admit reserved authority")
    if obj.get("zero_warning_required") is not True or obj.get("zero_unresolved_review_required") is not True:
        raise ClosureError("warnings and unresolved reviews must block")
    if obj.get("repository_bot_write") != "DENIED_UNTIL_DA_G4":
        raise ClosureError("repository bot write must remain denied")
    if obj.get("direct_main_write") != "PROHIBITED" or obj.get("force_push") != "PROHIBITED" or obj.get("history_rewrite") != "PROHIBITED":
        raise ClosureError("permanent repository safety boundaries may not be weakened")
    heads = _string_tuple(obj.get("allowed_head_patterns"), "allowed_head_patterns")
    paths = _string_tuple(obj.get("allowed_path_patterns"), "allowed_path_patterns")
    policy_id = _string(obj.get("policy_id"), "policy_id")
    programme_id = _string(obj.get("programme_id"), "programme_id")
    return ClosurePolicy(
        policy_id=policy_id,
        programme_id=programme_id,
        base_branch="main",
        merge_method="squash",
        exact_head_required=True,
        allowed_head_patterns=heads,
        allowed_path_patterns=paths,
        required_qa_status=_string(obj.get("required_qa_status"), "required_qa_status"),
        required_decision=_string(obj.get("required_decision"), "required_decision"),
        required_reserved_authority_delta="NONE",
        zero_warning_required=True,
        zero_unresolved_review_required=True,
        repository_bot_write="DENIED_UNTIL_DA_G4",
        direct_main_write="PROHIBITED",
        force_push="PROHIBITED",
        history_rewrite="PROHIBITED",
        policy_hash=canonical_sha256(obj, role="CLOSURE_POLICY"),
    )


def load_closure_policy(path: Path) -> ClosurePolicy:
    if path.suffix.lower() != ".json":
        raise ClosureError("runtime closure policies must use JSON")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClosureError(f"cannot load closure policy: {exc}") from exc
    if not isinstance(obj, dict):
        raise ClosureError("closure policy root must be an object")
    return parse_closure_policy(obj)


def parse_closure_snapshot(obj: Mapping[str, Any]) -> ClosureSnapshot:
    expected = {
        "schema", "policy_id", "policy_hash", "plan_id", "plan_version", "programme_id",
        "packet_id", "gate_id", "pull_request", "base_branch", "baseline_commit",
        "head_branch", "head_sha", "changed_files", "required_checks", "qa_status",
        "decision", "decision_id", "authority_delta", "reserved_authority_delta",
        "blockers", "warnings", "unresolved_review_count", "rollback", "next_packet",
    }
    if set(obj) != expected:
        raise ClosureError(f"closure snapshot fields mismatch: {sorted(set(obj) ^ expected)}")
    if obj.get("schema") != "ovc-closure-snapshot/v1":
        raise ClosureError("unsupported closure snapshot schema")
    pull_request = obj.get("pull_request")
    if not isinstance(pull_request, int) or isinstance(pull_request, bool) or pull_request <= 0:
        raise ClosureError("pull_request must be a positive integer")
    review_count = obj.get("unresolved_review_count")
    if not isinstance(review_count, int) or isinstance(review_count, bool) or review_count < 0:
        raise ClosureError("unresolved_review_count must be a non-negative integer")

    raw_checks = obj.get("required_checks")
    if not isinstance(raw_checks, list) or not raw_checks:
        raise ClosureError("required_checks must be a non-empty list")
    checks: list[WorkflowResult] = []
    identities: set[tuple[str, int]] = set()
    for row in raw_checks:
        if not isinstance(row, dict) or set(row) != {"name", "run_id", "result"}:
            raise ClosureError("invalid required check")
        run_id = row["run_id"]
        if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
            raise ClosureError("workflow run_id must be positive")
        check = WorkflowResult(_string(row["name"], "check.name"), run_id, _string(row["result"], "check.result"))
        identity = (check.name, check.run_id)
        if identity in identities:
            raise ClosureError("duplicate required check")
        identities.add(identity)
        checks.append(check)

    changed_files = tuple(sorted(normalize_relative_path(path) for path in _string_tuple(obj.get("changed_files"), "changed_files")))
    if len(changed_files) != len(set(changed_files)):
        raise ClosureError("changed_files normalize to duplicates")
    return ClosureSnapshot(
        policy_id=_string(obj.get("policy_id"), "policy_id"),
        policy_hash=_string(obj.get("policy_hash"), "policy_hash"),
        plan_id=_string(obj.get("plan_id"), "plan_id"),
        plan_version=_string(obj.get("plan_version"), "plan_version"),
        programme_id=_string(obj.get("programme_id"), "programme_id"),
        packet_id=_string(obj.get("packet_id"), "packet_id"),
        gate_id=_string(obj.get("gate_id"), "gate_id"),
        pull_request=pull_request,
        base_branch=_string(obj.get("base_branch"), "base_branch"),
        baseline_commit=_string(obj.get("baseline_commit"), "baseline_commit"),
        head_branch=_string(obj.get("head_branch"), "head_branch"),
        head_sha=_string(obj.get("head_sha"), "head_sha"),
        changed_files=changed_files,
        required_checks=tuple(sorted(checks, key=lambda row: (row.name, row.run_id))),
        qa_status=_string(obj.get("qa_status"), "qa_status"),
        decision=_string(obj.get("decision"), "decision"),
        decision_id=_string(obj.get("decision_id"), "decision_id"),
        authority_delta=_string(obj.get("authority_delta"), "authority_delta"),
        reserved_authority_delta=_string(obj.get("reserved_authority_delta"), "reserved_authority_delta"),
        blockers=_string_tuple(obj.get("blockers"), "blockers", allow_empty=True),
        warnings=_string_tuple(obj.get("warnings"), "warnings", allow_empty=True),
        unresolved_review_count=review_count,
        rollback=_string(obj.get("rollback"), "rollback"),
        next_packet=_string(obj.get("next_packet"), "next_packet"),
    )


def load_closure_snapshot(path: Path) -> ClosureSnapshot:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClosureError(f"cannot load closure snapshot: {exc}") from exc
    if not isinstance(obj, dict):
        raise ClosureError("closure snapshot root must be an object")
    return parse_closure_snapshot(obj)


def _safe_rollback(text: str) -> bool:
    lowered = text.lower()
    forbidden = ("git reset --hard", "force-push", "force push", "rewrite history", "delete accepted", "delete canonical")
    return not any(token in lowered for token in forbidden)


def evaluate_closure(snapshot: ClosureSnapshot, policy: ClosurePolicy) -> dict[str, Any]:
    reasons: list[str] = []
    if snapshot.policy_id != policy.policy_id or snapshot.policy_hash != policy.policy_hash:
        reasons.append("POLICY_IDENTITY_MISMATCH")
    if snapshot.programme_id != policy.programme_id:
        reasons.append("PROGRAMME_MISMATCH")
    if snapshot.base_branch != policy.base_branch:
        reasons.append("BASE_BRANCH_NOT_MAIN")
    if not _SHA.fullmatch(snapshot.baseline_commit):
        reasons.append("INVALID_BASELINE_SHA")
    if not _SHA.fullmatch(snapshot.head_sha):
        reasons.append("INVALID_HEAD_SHA")
    if snapshot.baseline_commit == snapshot.head_sha:
        reasons.append("HEAD_EQUALS_BASELINE")
    if snapshot.head_branch == "main" or not any(fnmatchcase(snapshot.head_branch, pattern) for pattern in policy.allowed_head_patterns):
        reasons.append("HEAD_BRANCH_NOT_ALLOWED")
    for path in snapshot.changed_files:
        if not any(fnmatchcase(path, pattern) for pattern in policy.allowed_path_patterns):
            reasons.append(f"CHANGED_PATH_NOT_ALLOWED:{path}")
    if any(row.result != "PASS" for row in snapshot.required_checks):
        reasons.append("REQUIRED_CHECK_NOT_PASS")
    if snapshot.qa_status != policy.required_qa_status:
        reasons.append("QA_STATUS_NOT_PASS")
    if snapshot.decision != policy.required_decision:
        reasons.append("DECISION_NOT_PASS")
    if snapshot.reserved_authority_delta != policy.required_reserved_authority_delta:
        reasons.append("RESERVED_AUTHORITY_DELTA")
    if snapshot.blockers:
        reasons.append("BLOCKERS_PRESENT")
    if policy.zero_warning_required and snapshot.warnings:
        reasons.append("WARNINGS_PRESENT")
    if policy.zero_unresolved_review_required and snapshot.unresolved_review_count != 0:
        reasons.append("UNRESOLVED_REVIEWS_PRESENT")
    if not _safe_rollback(snapshot.rollback):
        reasons.append("DESTRUCTIVE_ROLLBACK")

    reasons = sorted(set(reasons))
    status = "PASS" if not reasons else "BLOCK"
    logical = {
        "schema": "ovc-closure-proposal/v1",
        "snapshot_id": snapshot.snapshot_id,
        "policy_id": policy.policy_id,
        "policy_hash": policy.policy_hash,
        "programme_id": snapshot.programme_id,
        "packet_id": snapshot.packet_id,
        "gate_id": snapshot.gate_id,
        "pull_request": snapshot.pull_request,
        "base_branch": snapshot.base_branch,
        "baseline_commit": snapshot.baseline_commit,
        "head_branch": snapshot.head_branch,
        "head_sha": snapshot.head_sha,
        "changed_files": list(snapshot.changed_files),
        "status": status,
        "blockers": reasons,
        "proposed_merge_method": policy.merge_method,
        "exact_head_required": policy.exact_head_required,
        "eligible_for_manual_squash_merge": status == "PASS",
        "next_packet": snapshot.next_packet,
        "authority": {
            "dry_run_only": True,
            "writes_performed": False,
            "merge_performed": False,
            "repository_bot_write": "DENIED",
            "direct_main_write": "DENIED",
            "force_push": "DENIED",
            "history_rewrite": "DENIED",
        },
    }
    return {**logical, "closure_proposal_id": canonical_sha256(logical, role="CLOSURE_PROPOSAL")}


def propose_merge_receipt(snapshot: ClosureSnapshot, policy: ClosurePolicy, merge_sha: str) -> dict[str, Any]:
    closure = evaluate_closure(snapshot, policy)
    if closure["status"] != "PASS":
        raise ClosureError("blocked closure cannot produce a receipt proposal")
    if not _SHA.fullmatch(merge_sha) or merge_sha in {snapshot.baseline_commit, snapshot.head_sha}:
        raise ClosureError("merge_sha must be a distinct lowercase Git SHA")
    material = {
        "schema": "ovc-development-acceleration-merge-receipt/v1",
        "programme_id": snapshot.programme_id,
        "packet_id": snapshot.packet_id,
        "gate_id": snapshot.gate_id,
        "pull_request": snapshot.pull_request,
        "approved_head_sha": snapshot.head_sha,
        "squash_merge_sha": merge_sha,
        "decision": snapshot.decision,
        "decision_id": snapshot.decision_id,
        "authority_delta": snapshot.authority_delta,
        "required_checks": [row.to_dict() for row in snapshot.required_checks],
        "rollback": snapshot.rollback,
        "next_packet": snapshot.next_packet,
    }
    logical = {
        "schema": "ovc-merge-receipt-proposal/v1",
        "closure_proposal_id": closure["closure_proposal_id"],
        "receipt": material,
        "proposal_only": True,
        "authority": closure["authority"],
    }
    return {**logical, "receipt_proposal_id": canonical_sha256(logical, role="MERGE_RECEIPT_PROPOSAL")}


def _differences(left: Any, right: Any, path: str = "$") -> list[str]:
    if type(left) is not type(right):
        return [f"{path}:TYPE"]
    if isinstance(left, dict):
        differences: list[str] = []
        for key in sorted(set(left) | set(right)):
            if key not in left:
                differences.append(f"{path}.{key}:MISSING_PROPOSAL")
            elif key not in right:
                differences.append(f"{path}.{key}:EXTRA_PROPOSAL")
            else:
                differences.extend(_differences(left[key], right[key], f"{path}.{key}"))
        return differences
    if isinstance(left, list):
        if len(left) != len(right):
            return [f"{path}:LENGTH"]
        differences: list[str] = []
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            differences.extend(_differences(left_item, right_item, f"{path}[{index}]"))
        return differences
    return [] if left == right else [f"{path}:VALUE"]


def compare_receipt_proposal(proposal: Mapping[str, Any], manual_receipt: Mapping[str, Any]) -> dict[str, Any]:
    if proposal.get("schema") != "ovc-merge-receipt-proposal/v1" or proposal.get("proposal_only") is not True:
        raise ClosureError("invalid merge receipt proposal")
    receipt = proposal.get("receipt")
    if not isinstance(receipt, dict) or not isinstance(manual_receipt, dict):
        raise ClosureError("receipt comparison requires objects")
    differences = _differences(receipt, dict(manual_receipt))
    logical = {
        "schema": "ovc-receipt-comparison/v1",
        "receipt_proposal_id": proposal.get("receipt_proposal_id"),
        "manual_receipt_hash": canonical_sha256(manual_receipt, role="MANUAL_MERGE_RECEIPT"),
        "status": "PASS" if not differences else "BLOCK",
        "differences": differences,
        "material_fields_equal": not differences,
        "authority": {
            "dry_run_only": True,
            "writes_performed": False,
            "merge_performed": False,
            "repository_bot_write": "DENIED",
            "direct_main_write": "DENIED",
            "force_push": "DENIED",
        },
    }
    return {**logical, "comparison_id": canonical_sha256(logical, role="RECEIPT_COMPARISON")}

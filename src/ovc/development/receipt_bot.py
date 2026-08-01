"""Fail-closed receipt-bot planning and bounded adapter services.

The module never performs GitHub operations directly.  It validates immutable
work packets, emits deterministic action plans and can drive only an injected
adapter exposing create-branch, put-file and open-PR methods.  Merge, approval,
review dismissal, deletion, force-push and authority mutation are deliberately
absent from the adapter protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
import json
from pathlib import Path
import re
from typing import Any, Mapping, Protocol, Sequence

from .identity import IdentityError, canonical_sha256, normalize_relative_path


class ReceiptBotError(ValueError):
    """Raised when policy, work-packet or activation evidence is invalid."""


_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDEMPOTENCY = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{7,127}$")
_FORBIDDEN_ROLLBACK = (
    "git reset --hard",
    "force-push",
    "force push",
    "rewrite history",
    "delete accepted",
    "delete canonical",
)
_SECRET_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9_]{8,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{8,}"),
    re.compile(r"sk-proj-[A-Za-z0-9_-]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


@dataclass(frozen=True)
class TargetFile:
    path: str
    content_sha256: str

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "content_sha256": self.content_sha256}


@dataclass(frozen=True)
class ReceiptBotPolicy:
    policy_id: str
    programme_id: str
    approved_profile_id: str
    approved_profile_hash: str
    active: bool
    base_branch: str
    branch_patterns: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    denied_actions: tuple[str, ...]
    required_activation_conditions: tuple[str, ...]
    policy_hash: str


@dataclass(frozen=True)
class ReceiptBotWorkPacket:
    profile_id: str
    profile_hash: str
    programme_id: str
    packet_id: str
    source_main_sha: str
    current_main_sha: str
    branch: str
    pull_request_title: str
    target_files: tuple[TargetFile, ...]
    closure_status: str
    qa_status: str
    decision: str
    reserved_authority_delta: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    unresolved_review_count: int
    rollback: str
    idempotency_key: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "profile_hash": self.profile_hash,
            "programme_id": self.programme_id,
            "packet_id": self.packet_id,
            "source_main_sha": self.source_main_sha,
            "current_main_sha": self.current_main_sha,
            "branch": self.branch,
            "pull_request_title": self.pull_request_title,
            "target_files": [row.to_dict() for row in self.target_files],
            "closure_status": self.closure_status,
            "qa_status": self.qa_status,
            "decision": self.decision,
            "reserved_authority_delta": self.reserved_authority_delta,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "unresolved_review_count": self.unresolved_review_count,
            "rollback": self.rollback,
            "idempotency_key": self.idempotency_key,
        }

    @property
    def packet_hash(self) -> str:
        return canonical_sha256(self.to_dict(), role="RECEIPT_BOT_WORK_PACKET")


class RepositoryProposalAdapter(Protocol):
    """Narrow transport boundary.  No merge or approval methods exist."""

    def create_branch(self, *, branch: str, source_sha: str) -> Mapping[str, Any]: ...

    def put_file(self, *, branch: str, path: str, content_sha256: str) -> Mapping[str, Any]: ...

    def open_pull_request(self, *, branch: str, base: str, title: str) -> Mapping[str, Any]: ...


class RecordingProposalAdapter:
    """Deterministic in-memory adapter used for denied-action and order tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create_branch(self, *, branch: str, source_sha: str) -> Mapping[str, Any]:
        row = {"action": "CREATE_BOT_BRANCH", "branch": branch, "source_sha": source_sha}
        self.calls.append(row)
        return row

    def put_file(self, *, branch: str, path: str, content_sha256: str) -> Mapping[str, Any]:
        row = {
            "action": "CREATE_OR_UPDATE_ALLOWLISTED_FILES",
            "branch": branch,
            "path": path,
            "content_sha256": content_sha256,
        }
        self.calls.append(row)
        return row

    def open_pull_request(self, *, branch: str, base: str, title: str) -> Mapping[str, Any]:
        row = {"action": "OPEN_OR_UPDATE_PULL_REQUEST", "branch": branch, "base": base, "title": title}
        self.calls.append(row)
        return row


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReceiptBotError(f"{field} must be a non-empty string")
    return value


def _string_tuple(value: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "possibly empty" if allow_empty else "non-empty"
        raise ReceiptBotError(f"{field} must be a {qualifier} list")
    result = tuple(_string(item, field) for item in value)
    if len(result) != len(set(result)):
        raise ReceiptBotError(f"{field} contains duplicates")
    return result


def parse_policy(obj: Mapping[str, Any]) -> ReceiptBotPolicy:
    expected = {
        "schema",
        "policy_id",
        "programme_id",
        "approved_profile_id",
        "approved_profile_hash",
        "active",
        "base_branch",
        "branch_patterns",
        "allowed_paths",
        "allowed_actions",
        "denied_actions",
        "required_activation_conditions",
    }
    if set(obj) != expected:
        raise ReceiptBotError(f"policy fields mismatch: {sorted(set(obj) ^ expected)}")
    if obj.get("schema") != "ovc-receipt-bot-policy/v1":
        raise ReceiptBotError("unsupported receipt-bot policy schema")
    if obj.get("active") is not False:
        raise ReceiptBotError("repository-bot policy must remain inactive until activation evidence passes")
    if obj.get("base_branch") != "main":
        raise ReceiptBotError("base branch must be main")
    allowed_actions = _string_tuple(obj.get("allowed_actions"), "allowed_actions")
    if allowed_actions != (
        "CREATE_BOT_BRANCH",
        "CREATE_OR_UPDATE_ALLOWLISTED_FILES",
        "OPEN_OR_UPDATE_PULL_REQUEST",
    ):
        raise ReceiptBotError("allowed action set is not the approved minimal set")
    denied = _string_tuple(obj.get("denied_actions"), "denied_actions")
    required_denials = {
        "WRITE_MAIN",
        "WRITE_NON_BOT_BRANCH",
        "MERGE_PULL_REQUEST",
        "APPROVE_PULL_REQUEST",
        "DISMISS_REVIEW",
        "FORCE_PUSH",
        "REWRITE_HISTORY",
        "DELETE_BRANCH",
        "DELETE_ACCEPTED_RECORD",
        "MODIFY_AUTHORITY_PROFILE",
        "SELF_APPROVE",
        "PROVIDER_ACCESS",
        "R2_WRITE",
        "RELEASE_PUBLICATION",
        "SELECTOR_MUTATION",
        "VALIDATION_ACCESS",
        "MARKET_OR_SEMANTIC_MUTATION",
        "PROBABILITY_RISK_EXPOSURE_OR_EXECUTION_OBJECT",
    }
    if not required_denials.issubset(set(denied)):
        raise ReceiptBotError("permanent denial set is incomplete")
    profile_hash = _string(obj.get("approved_profile_hash"), "approved_profile_hash")
    if not _SHA256.fullmatch(profile_hash):
        raise ReceiptBotError("approved_profile_hash must be lowercase SHA-256")
    return ReceiptBotPolicy(
        policy_id=_string(obj.get("policy_id"), "policy_id"),
        programme_id=_string(obj.get("programme_id"), "programme_id"),
        approved_profile_id=_string(obj.get("approved_profile_id"), "approved_profile_id"),
        approved_profile_hash=profile_hash,
        active=False,
        base_branch="main",
        branch_patterns=_string_tuple(obj.get("branch_patterns"), "branch_patterns"),
        allowed_paths=_string_tuple(obj.get("allowed_paths"), "allowed_paths"),
        allowed_actions=allowed_actions,
        denied_actions=denied,
        required_activation_conditions=_string_tuple(
            obj.get("required_activation_conditions"), "required_activation_conditions"
        ),
        policy_hash=canonical_sha256(obj, role="RECEIPT_BOT_POLICY"),
    )


def load_policy(path: Path) -> ReceiptBotPolicy:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptBotError(f"cannot load receipt-bot policy: {exc}") from exc
    if not isinstance(obj, dict):
        raise ReceiptBotError("receipt-bot policy root must be an object")
    return parse_policy(obj)


def parse_work_packet(obj: Mapping[str, Any]) -> ReceiptBotWorkPacket:
    expected = {
        "schema",
        "profile_id",
        "profile_hash",
        "programme_id",
        "packet_id",
        "source_main_sha",
        "current_main_sha",
        "branch",
        "pull_request_title",
        "target_files",
        "closure_status",
        "qa_status",
        "decision",
        "reserved_authority_delta",
        "blockers",
        "warnings",
        "unresolved_review_count",
        "rollback",
        "idempotency_key",
    }
    if set(obj) != expected:
        raise ReceiptBotError(f"work-packet fields mismatch: {sorted(set(obj) ^ expected)}")
    if obj.get("schema") != "ovc-receipt-bot-work-packet/v1":
        raise ReceiptBotError("unsupported receipt-bot work-packet schema")
    raw_targets = obj.get("target_files")
    if not isinstance(raw_targets, list) or not raw_targets:
        raise ReceiptBotError("target_files must be a non-empty list")
    targets: list[TargetFile] = []
    paths: set[str] = set()
    for row in raw_targets:
        if not isinstance(row, dict) or set(row) != {"path", "content_sha256"}:
            raise ReceiptBotError("invalid target file")
        try:
            path = normalize_relative_path(_string(row.get("path"), "target.path"))
        except IdentityError as exc:
            raise ReceiptBotError(f"invalid target path: {exc}") from exc
        digest = _string(row.get("content_sha256"), "target.content_sha256")
        if not _SHA256.fullmatch(digest):
            raise ReceiptBotError("target content hash must be lowercase SHA-256")
        if path in paths:
            raise ReceiptBotError("target paths normalize to duplicates")
        paths.add(path)
        targets.append(TargetFile(path, digest))
    review_count = obj.get("unresolved_review_count")
    if not isinstance(review_count, int) or isinstance(review_count, bool) or review_count < 0:
        raise ReceiptBotError("unresolved_review_count must be a non-negative integer")
    key = _string(obj.get("idempotency_key"), "idempotency_key")
    if not _IDEMPOTENCY.fullmatch(key):
        raise ReceiptBotError("idempotency_key has invalid syntax")
    return ReceiptBotWorkPacket(
        profile_id=_string(obj.get("profile_id"), "profile_id"),
        profile_hash=_string(obj.get("profile_hash"), "profile_hash"),
        programme_id=_string(obj.get("programme_id"), "programme_id"),
        packet_id=_string(obj.get("packet_id"), "packet_id"),
        source_main_sha=_string(obj.get("source_main_sha"), "source_main_sha"),
        current_main_sha=_string(obj.get("current_main_sha"), "current_main_sha"),
        branch=_string(obj.get("branch"), "branch"),
        pull_request_title=_string(obj.get("pull_request_title"), "pull_request_title"),
        target_files=tuple(sorted(targets, key=lambda item: item.path)),
        closure_status=_string(obj.get("closure_status"), "closure_status"),
        qa_status=_string(obj.get("qa_status"), "qa_status"),
        decision=_string(obj.get("decision"), "decision"),
        reserved_authority_delta=_string(obj.get("reserved_authority_delta"), "reserved_authority_delta"),
        blockers=_string_tuple(obj.get("blockers"), "blockers", allow_empty=True),
        warnings=_string_tuple(obj.get("warnings"), "warnings", allow_empty=True),
        unresolved_review_count=review_count,
        rollback=_string(obj.get("rollback"), "rollback"),
        idempotency_key=key,
    )


def load_work_packet(path: Path) -> ReceiptBotWorkPacket:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptBotError(f"cannot load receipt-bot work packet: {exc}") from exc
    if not isinstance(obj, dict):
        raise ReceiptBotError("receipt-bot work-packet root must be an object")
    return parse_work_packet(obj)


def redact_secrets(value: Any) -> Any:
    """Return a recursively redacted copy suitable for deterministic audit records."""
    if isinstance(value, str):
        result = value
        for pattern in _SECRET_PATTERNS:
            result = pattern.sub("[REDACTED]", result)
        return result
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    if isinstance(value, dict):
        return {str(key): redact_secrets(item) for key, item in value.items()}
    return value


def _rollback_is_safe(text: str) -> bool:
    lowered = text.lower()
    return not any(token in lowered for token in _FORBIDDEN_ROLLBACK)


def evaluate_work_packet(
    packet: ReceiptBotWorkPacket,
    policy: ReceiptBotPolicy,
    *,
    idempotency_ledger: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    if packet.profile_id != policy.approved_profile_id or packet.profile_hash != policy.approved_profile_hash:
        blockers.append("APPROVED_PROFILE_IDENTITY_MISMATCH")
    if packet.programme_id != policy.programme_id:
        blockers.append("PROGRAMME_MISMATCH")
    if not _SHA40.fullmatch(packet.source_main_sha) or not _SHA40.fullmatch(packet.current_main_sha):
        blockers.append("INVALID_MAIN_SHA")
    elif packet.source_main_sha != packet.current_main_sha:
        blockers.append("STALE_MAIN_SHA")
    if packet.branch == "main" or not any(fnmatchcase(packet.branch, pattern) for pattern in policy.branch_patterns):
        blockers.append("BRANCH_NOT_ALLOWED")
    for target in packet.target_files:
        if not any(fnmatchcase(target.path, pattern) for pattern in policy.allowed_paths):
            blockers.append(f"PATH_NOT_ALLOWED:{target.path}")
    if packet.closure_status != "PASS":
        blockers.append("CLOSURE_NOT_PASS")
    if packet.qa_status != "PASS":
        blockers.append("QA_NOT_PASS")
    if packet.decision != "PASS":
        blockers.append("DECISION_NOT_PASS")
    if packet.reserved_authority_delta != "NONE":
        blockers.append("RESERVED_AUTHORITY_DELTA")
    if packet.blockers:
        blockers.append("BLOCKERS_PRESENT")
    if packet.warnings:
        blockers.append("WARNINGS_PRESENT")
    if packet.unresolved_review_count != 0:
        blockers.append("UNRESOLVED_REVIEWS_PRESENT")
    if not _rollback_is_safe(packet.rollback):
        blockers.append("DESTRUCTIVE_ROLLBACK")

    logical_plan = {
        "schema": "ovc-receipt-bot-action-plan/v1",
        "policy_id": policy.policy_id,
        "policy_hash": policy.policy_hash,
        "profile_id": packet.profile_id,
        "profile_hash": packet.profile_hash,
        "programme_id": packet.programme_id,
        "packet_id": packet.packet_id,
        "work_packet_hash": packet.packet_hash,
        "source_main_sha": packet.source_main_sha,
        "branch": packet.branch,
        "base_branch": policy.base_branch,
        "pull_request_title": packet.pull_request_title,
        "target_files": [row.to_dict() for row in packet.target_files],
        "idempotency_key": packet.idempotency_key,
        "actions": [
            {"action": "CREATE_BOT_BRANCH", "branch": packet.branch, "source_sha": packet.source_main_sha},
            *[
                {
                    "action": "CREATE_OR_UPDATE_ALLOWLISTED_FILES",
                    "branch": packet.branch,
                    "path": target.path,
                    "content_sha256": target.content_sha256,
                }
                for target in packet.target_files
            ],
            {
                "action": "OPEN_OR_UPDATE_PULL_REQUEST",
                "branch": packet.branch,
                "base": policy.base_branch,
                "title": packet.pull_request_title,
            },
        ],
        "authority": {
            "approved_for_implementation": True,
            "active": False,
            "writes_performed": False,
            "merge_api_available": False,
            "direct_main_write": "PROHIBITED",
            "force_push": "PROHIBITED",
            "history_rewrite": "PROHIBITED",
        },
    }
    plan_id = canonical_sha256(logical_plan, role="RECEIPT_BOT_ACTION_PLAN")
    ledger = idempotency_ledger or {}
    prior = ledger.get(packet.idempotency_key)
    idempotency_status = "NEW"
    if prior is not None:
        if prior == plan_id:
            idempotency_status = "IDEMPOTENT_RETRY"
        else:
            blockers.append("IDEMPOTENCY_COLLISION")
            idempotency_status = "COLLISION"

    blockers = sorted(set(blockers))
    return {
        **logical_plan,
        "plan_id": plan_id,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "idempotency_status": idempotency_status,
    }


def evaluate_activation(evidence: Mapping[str, str], policy: ReceiptBotPolicy) -> dict[str, Any]:
    missing = sorted(set(policy.required_activation_conditions) - set(evidence))
    non_pass = sorted(
        condition for condition in policy.required_activation_conditions if evidence.get(condition) != "PASS"
    )
    blockers = [*(f"MISSING:{item}" for item in missing), *(f"NOT_PASS:{item}" for item in non_pass)]
    blockers = sorted(set(blockers))
    return {
        "schema": "ovc-receipt-bot-activation-evaluation/v1",
        "policy_id": policy.policy_id,
        "policy_hash": policy.policy_hash,
        "required_conditions": list(policy.required_activation_conditions),
        "evidence": {key: evidence[key] for key in sorted(evidence)},
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "authority_active": not blockers,
        "evaluation_id": canonical_sha256(
            {
                "policy_id": policy.policy_id,
                "policy_hash": policy.policy_hash,
                "evidence": {key: evidence[key] for key in sorted(evidence)},
                "blockers": blockers,
            },
            role="RECEIPT_BOT_ACTIVATION_EVALUATION",
        ),
    }


def execute_plan(
    plan: Mapping[str, Any],
    adapter: RepositoryProposalAdapter,
    *,
    activation_evaluation: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute the three approved action classes only after activation PASS."""
    if plan.get("status") != "PASS":
        raise ReceiptBotError("blocked plan cannot execute")
    if activation_evaluation.get("status") != "PASS" or activation_evaluation.get("authority_active") is not True:
        raise ReceiptBotError("repository-bot authority is inactive")
    actions = plan.get("actions")
    if not isinstance(actions, list) or not actions:
        raise ReceiptBotError("action plan is missing actions")
    results: list[Mapping[str, Any]] = []
    for action in actions:
        kind = action.get("action")
        if kind == "CREATE_BOT_BRANCH":
            results.append(adapter.create_branch(branch=action["branch"], source_sha=action["source_sha"]))
        elif kind == "CREATE_OR_UPDATE_ALLOWLISTED_FILES":
            results.append(
                adapter.put_file(
                    branch=action["branch"],
                    path=action["path"],
                    content_sha256=action["content_sha256"],
                )
            )
        elif kind == "OPEN_OR_UPDATE_PULL_REQUEST":
            results.append(
                adapter.open_pull_request(
                    branch=action["branch"], base=action["base"], title=action["title"]
                )
            )
        else:
            raise ReceiptBotError(f"action is not allowed: {kind}")
    audit = {
        "schema": "ovc-receipt-bot-audit-event/v1",
        "plan_id": plan["plan_id"],
        "idempotency_key": plan["idempotency_key"],
        "actions": redact_secrets(results),
        "merge_performed": False,
        "approval_performed": False,
        "force_push_performed": False,
    }
    return {**audit, "audit_event_id": canonical_sha256(audit, role="RECEIPT_BOT_AUDIT_EVENT")}

"""Pre-activation receipt-bot shadow execution with permanent authority denials.

This module resolves the DA-G4B sequencing problem without activating repository-bot
write authority. A real shadow may run only after every external and static pre-shadow
condition passes, using a dedicated revocable GitHub App identity. The shadow can create
one allowlisted proposal branch, write one allowlisted receipt and open one unmerged PR.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
import hashlib
from typing import Any, Mapping, Protocol

from .identity import canonical_sha256
from .receipt_bot import ReceiptBotError, ReceiptBotPolicy, redact_secrets


_PRE_ACTIVATION_EXEMPT_CONDITIONS = frozenset({
    "REAL_PROPOSAL_BRANCH_SHADOW_PASS",
    "QA_PASS",
})
_SHADOW_PATH_PREFIX = "docs/releases/development-acceleration-v0-1/da-wp4b-shadow/"


@dataclass(frozen=True)
class ReceiptBotShadowIdentity:
    """Non-secret identity metadata for the dedicated revocable GitHub App."""

    app_id: int
    installation_id: int
    app_slug: str
    repository: str
    credential_kind: str
    revocable: bool
    operator_connector: bool
    permissions: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ovc-receipt-bot-shadow-identity/v1",
            "app_id": self.app_id,
            "installation_id": self.installation_id,
            "app_slug": self.app_slug,
            "repository": self.repository,
            "credential_kind": self.credential_kind,
            "revocable": self.revocable,
            "operator_connector": self.operator_connector,
            "permissions": dict(sorted(self.permissions.items())),
        }


class ShadowRepositoryProposalAdapter(Protocol):
    """Shadow-only transport. Merge, approval, deletion and force-push are absent."""

    def create_branch(self, *, branch: str, source_sha: str) -> Mapping[str, Any]: ...

    def put_file(
        self,
        *,
        branch: str,
        path: str,
        content: bytes,
        content_sha256: str,
    ) -> Mapping[str, Any]: ...

    def open_pull_request(self, *, branch: str, base: str, title: str) -> Mapping[str, Any]: ...


class RecordingShadowProposalAdapter:
    """Deterministic in-memory adapter for focused shadow tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create_branch(self, *, branch: str, source_sha: str) -> Mapping[str, Any]:
        row = {"action": "CREATE_BOT_BRANCH", "branch": branch, "source_sha": source_sha}
        self.calls.append(row)
        return row

    def put_file(
        self,
        *,
        branch: str,
        path: str,
        content: bytes,
        content_sha256: str,
    ) -> Mapping[str, Any]:
        digest = hashlib.sha256(content).hexdigest()
        if digest != content_sha256:
            raise ReceiptBotError("shadow adapter content hash mismatch")
        row = {
            "action": "CREATE_OR_UPDATE_ALLOWLISTED_FILES",
            "branch": branch,
            "path": path,
            "content_sha256": content_sha256,
            "byte_length": len(content),
        }
        self.calls.append(row)
        return row

    def open_pull_request(self, *, branch: str, base: str, title: str) -> Mapping[str, Any]:
        row = {"action": "OPEN_OR_UPDATE_PULL_REQUEST", "branch": branch, "base": base, "title": title}
        self.calls.append(row)
        return row


def parse_shadow_identity(obj: Mapping[str, Any]) -> ReceiptBotShadowIdentity:
    expected = {
        "schema",
        "app_id",
        "installation_id",
        "app_slug",
        "repository",
        "credential_kind",
        "revocable",
        "operator_connector",
        "permissions",
    }
    if set(obj) != expected:
        raise ReceiptBotError(f"shadow identity fields mismatch: {sorted(set(obj) ^ expected)}")
    if obj.get("schema") != "ovc-receipt-bot-shadow-identity/v1":
        raise ReceiptBotError("unsupported shadow identity schema")
    app_id = obj.get("app_id")
    installation_id = obj.get("installation_id")
    if not isinstance(app_id, int) or isinstance(app_id, bool) or app_id <= 0:
        raise ReceiptBotError("app_id must be a positive integer")
    if not isinstance(installation_id, int) or isinstance(installation_id, bool) or installation_id <= 0:
        raise ReceiptBotError("installation_id must be a positive integer")
    app_slug = obj.get("app_slug")
    repository = obj.get("repository")
    credential_kind = obj.get("credential_kind")
    if not isinstance(app_slug, str) or not app_slug.strip():
        raise ReceiptBotError("app_slug must be non-empty")
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise ReceiptBotError("repository must be owner/name")
    if credential_kind != "GITHUB_APP_INSTALLATION_TOKEN":
        raise ReceiptBotError("shadow credential must be a GitHub App installation token")
    if obj.get("revocable") is not True:
        raise ReceiptBotError("shadow identity must be independently revocable")
    if obj.get("operator_connector") is not False:
        raise ReceiptBotError("operator connector cannot substitute for the dedicated shadow identity")
    permissions = obj.get("permissions")
    required_permissions = {
        "contents": "write",
        "pull_requests": "write",
        "metadata": "read",
    }
    if not isinstance(permissions, dict) or permissions != required_permissions:
        raise ReceiptBotError("shadow identity permissions must match the exact minimal set")
    return ReceiptBotShadowIdentity(
        app_id=app_id,
        installation_id=installation_id,
        app_slug=app_slug.strip(),
        repository=repository,
        credential_kind=credential_kind,
        revocable=True,
        operator_connector=False,
        permissions=required_permissions,
    )


def evaluate_shadow_readiness(
    evidence: Mapping[str, str],
    policy: ReceiptBotPolicy,
) -> dict[str, Any]:
    """Evaluate the pre-activation conditions needed to run the one real shadow.

    REAL_PROPOSAL_BRANCH_SHADOW_PASS and final QA are outputs of the shadow sequence,
    so they cannot be prerequisites for starting it. Every other activation condition,
    including independently reproducible main-branch protection, must already PASS.
    """

    required = tuple(
        condition
        for condition in policy.required_activation_conditions
        if condition not in _PRE_ACTIVATION_EXEMPT_CONDITIONS
    )
    if not _PRE_ACTIVATION_EXEMPT_CONDITIONS.issubset(set(policy.required_activation_conditions)):
        raise ReceiptBotError("policy is missing required post-shadow activation conditions")
    missing = sorted(set(required) - set(evidence))
    non_pass = sorted(condition for condition in required if evidence.get(condition) != "PASS")
    blockers = sorted({
        *(f"MISSING:{condition}" for condition in missing),
        *(f"NOT_PASS:{condition}" for condition in non_pass),
    })
    logical = {
        "schema": "ovc-receipt-bot-shadow-readiness/v1",
        "policy_id": policy.policy_id,
        "policy_hash": policy.policy_hash,
        "required_pre_shadow_conditions": list(required),
        "post_shadow_conditions": sorted(_PRE_ACTIVATION_EXEMPT_CONDITIONS),
        "evidence": {key: evidence[key] for key in sorted(evidence)},
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "shadow_execution_authorized": not blockers,
        "authority_active": False,
    }
    return {
        **logical,
        "evaluation_id": canonical_sha256(logical, role="RECEIPT_BOT_SHADOW_READINESS"),
    }


def _resolve_shadow_content(
    plan: Mapping[str, Any],
    content_by_path: Mapping[str, bytes | str],
) -> tuple[str, bytes, str]:
    targets = plan.get("target_files")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        raise ReceiptBotError("pre-activation shadow must contain exactly one target file")
    target = targets[0]
    path = target.get("path")
    expected_hash = target.get("content_sha256")
    if not isinstance(path, str) or not path.startswith(_SHADOW_PATH_PREFIX) or not path.endswith(".json"):
        raise ReceiptBotError("shadow target must be one JSON receipt under the dedicated shadow path")
    if set(content_by_path) != {path}:
        raise ReceiptBotError("shadow content mapping must exactly match the approved target")
    raw = content_by_path[path]
    if isinstance(raw, str):
        content = raw.encode("utf-8")
    elif isinstance(raw, bytes):
        content = raw
    else:
        raise ReceiptBotError("shadow target content must be UTF-8 text or bytes")
    digest = hashlib.sha256(content).hexdigest()
    if digest != expected_hash:
        raise ReceiptBotError("shadow target content does not match the frozen SHA-256")
    decoded = content.decode("utf-8")
    if redact_secrets(decoded) != decoded:
        raise ReceiptBotError("shadow target contains credential-like material")
    return path, content, digest


def execute_pre_activation_shadow(
    plan: Mapping[str, Any],
    adapter: ShadowRepositoryProposalAdapter,
    *,
    shadow_readiness: Mapping[str, Any],
    identity: ReceiptBotShadowIdentity,
    content_by_path: Mapping[str, bytes | str],
) -> dict[str, Any]:
    """Run the single real proposal-branch rehearsal while authority stays inactive."""

    if plan.get("status") != "PASS":
        raise ReceiptBotError("blocked action plan cannot run a shadow")
    if plan.get("idempotency_status") != "NEW":
        raise ReceiptBotError("pre-activation shadow requires a new idempotency key")
    if shadow_readiness.get("status") != "PASS" or shadow_readiness.get("shadow_execution_authorized") is not True:
        raise ReceiptBotError("pre-activation shadow readiness did not pass")
    if shadow_readiness.get("authority_active") is not False:
        raise ReceiptBotError("shadow readiness must not activate repository-bot authority")
    parsed_identity = parse_shadow_identity(identity.to_dict())
    branch = plan.get("branch")
    title = plan.get("pull_request_title")
    base = plan.get("base_branch")
    source_sha = plan.get("source_main_sha")
    if not isinstance(branch, str) or branch == "main" or "/da-g4b-shadow-" not in branch:
        raise ReceiptBotError("shadow branch must use the dedicated DA-G4B shadow naming form")
    if not any(fnmatchcase(branch, pattern) for pattern in ("bot/ovc-dev-accel-receipts/*",)):
        raise ReceiptBotError("shadow branch is outside the approved bot namespace")
    if not isinstance(title, str) or "da-g4b" not in title.lower() or "shadow" not in title.lower():
        raise ReceiptBotError("shadow PR title must identify DA-G4B and shadow status")
    if base != "main":
        raise ReceiptBotError("shadow PR must target main")
    if not isinstance(source_sha, str):
        raise ReceiptBotError("shadow source main SHA is missing")
    path, content, digest = _resolve_shadow_content(plan, content_by_path)

    results = [
        adapter.create_branch(branch=branch, source_sha=source_sha),
        adapter.put_file(
            branch=branch,
            path=path,
            content=content,
            content_sha256=digest,
        ),
        adapter.open_pull_request(branch=branch, base="main", title=title),
    ]
    audit = {
        "schema": "ovc-receipt-bot-pre-activation-shadow-audit/v1",
        "mode": "PRE_ACTIVATION_SHADOW",
        "plan_id": plan.get("plan_id"),
        "idempotency_key": plan.get("idempotency_key"),
        "identity": parsed_identity.to_dict(),
        "shadow_readiness_id": shadow_readiness.get("evaluation_id"),
        "actions": redact_secrets(results),
        "target_path": path,
        "target_content_sha256": digest,
        "shadow_result": "PASS",
        "authority_active": False,
        "production_transport_active": False,
        "merge_performed": False,
        "approval_performed": False,
        "force_push_performed": False,
        "history_rewrite_performed": False,
    }
    return {
        **audit,
        "audit_event_id": canonical_sha256(audit, role="RECEIPT_BOT_PRE_ACTIVATION_SHADOW_AUDIT"),
    }

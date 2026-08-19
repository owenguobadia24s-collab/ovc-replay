from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence


DENY_PRECEDENCE = (
    "HARD_DENY_OR_UNKNOWN",
    "QUIESCENCE",
    "OPERATOR_BOUNDARY",
    "OWNER_AUTHORITY",
    "ADMISSION",
    "EXECUTOR",
    "ACTION_SIDE_EFFECT_WRITE_DOMAIN",
    "PREREQUISITE_DEPENDENCY",
    "RUNNABLE",
)


def _canonical(value: Any) -> str:
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return sha256(raw).hexdigest()


@dataclass(frozen=True)
class PersistentWorkRequest:
    programme_id: str
    current_state_root: str
    governing_plan_id: str
    packet_id: str
    packet_class: str
    authority_class: str
    authority_required: str
    owner_authority_source: str | None
    owner_authority_current: bool
    executor_binding_id: str | None
    action: str
    side_effect_class: str
    write_domain: str | None
    semantic_owner: str | None
    write_domain_declared: bool
    semantic_owner_match: bool
    prerequisites_pass: bool
    dependency_frontier_current: bool
    current_pointer_resolved: bool = True
    operator_boundary: bool = False
    priority: int = 100

    @property
    def request_id(self) -> str:
        return _canonical(self)


@dataclass(frozen=True)
class PersistentAuthorityView:
    programme_id: str
    packet_id: str
    request_id: str
    decision: str
    primary_reason: str
    reason_codes: tuple[str, ...]
    authority_effect: str = "NONE"

    @property
    def view_id(self) -> str:
        return _canonical(self)


@dataclass(frozen=True)
class PersistentDispatchProposal:
    programme_id: str
    packet_id: str
    request_id: str
    authority_view_id: str
    executor_identity: str
    action: str
    write_domain: str | None
    semantic_owner: str | None
    fencing_generation: int

    @property
    def dispatch_id(self) -> str:
        return _canonical(self)


@dataclass(frozen=True)
class PersistentReconciliationResult:
    snapshot_id: str
    views: tuple[PersistentAuthorityView, ...]
    dispatches: tuple[PersistentDispatchProposal, ...]

    @property
    def result_id(self) -> str:
        return _canonical(self)


def _registry_entry(action_registry: Mapping[str, Any], action: str) -> Mapping[str, Any] | None:
    for entry in action_registry.get("entries", ()):
        if str(entry.get("action")) == action:
            return entry
    return None


def derive_authority_view(
    request: PersistentWorkRequest,
    *,
    admission: Mapping[str, Any] | None,
    policy: Mapping[str, Any],
    executor_binding: Mapping[str, Any] | None,
    action_registry: Mapping[str, Any],
    quiescence_mode: str,
) -> PersistentAuthorityView:
    """Return a deterministic, authority-inert allow/park/deny view.

    The function is deliberately fail closed.  It only evaluates authority already
    present in the supplied immutable records.  It never creates admission,
    executor, packet, merge, scientific or repository-main authority.
    """

    reasons: list[str] = []

    # HARD_DENY / UNKNOWN.
    if not request.current_pointer_resolved:
        reasons.append("CURRENT_POINTER_UNRESOLVED")
    if request.action in set(map(str, action_registry.get("explicit_denies", ()))):
        reasons.append("ACTION_EXPLICITLY_DENIED")
    if request.side_effect_class in {"IRREVERSIBLE", "IRREVERSIBLE_OR_UNKNOWN", "UNKNOWN"}:
        reasons.append("SIDE_EFFECT_UNKNOWN_OR_DENIED")
    if request.authority_class not in set(map(str, policy.get("allowed_authority_classes", ()))):
        reasons.append("AUTHORITY_CLASS_NOT_ALLOWED")
    if request.authority_required == "OPERATOR_REQUIRED" or request.operator_boundary:
        # Kept for precedence below, but an operator boundary is never ALLOW.
        pass
    if reasons:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", reasons[0], tuple(reasons))

    # QUIESCENCE.
    if quiescence_mode in {"HOLD", "DISABLE_NEW_DISPATCH"}:
        return PersistentAuthorityView(
            request.programme_id,
            request.packet_id,
            request.request_id,
            "PARK",
            f"QUIESCENCE_{quiescence_mode}",
            (f"QUIESCENCE_{quiescence_mode}",),
        )
    if quiescence_mode not in {"RUN", "DRAIN"}:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "QUIESCENCE_UNKNOWN", ("QUIESCENCE_UNKNOWN",))

    # OPERATOR BOUNDARY.
    if request.authority_required == "OPERATOR_REQUIRED" or request.operator_boundary:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "PARK", "OPERATOR_REQUIRED_BOUNDARY", ("OPERATOR_REQUIRED_BOUNDARY",))

    # OWNER AUTHORITY.
    if not request.owner_authority_source:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "OWNER_AUTHORITY_UNKNOWN", ("OWNER_AUTHORITY_UNKNOWN",))
    if not request.owner_authority_current:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "OWNER_AUTHORITY_STALE_OR_REMOVED", ("OWNER_AUTHORITY_STALE_OR_REMOVED",))

    # ADMISSION.
    if admission is None:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "PROGRAMME_NOT_ADMITTED", ("PROGRAMME_NOT_ADMITTED",))
    if admission.get("status") != "ACTIVE":
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "PROGRAMME_ADMISSION_INACTIVE", ("PROGRAMME_ADMISSION_INACTIVE",))
    exact_admission_checks = (
        (admission.get("programme_id") == request.programme_id, "PROGRAMME_ADMISSION_MISMATCH"),
        (admission.get("current_state_root") == request.current_state_root, "PROGRAMME_ROOT_STALE"),
        (admission.get("governing_plan_id") == request.governing_plan_id, "GOVERNING_PLAN_MISMATCH"),
        (admission.get("owner_authority_source") == request.owner_authority_source, "OWNER_AUTHORITY_SOURCE_MISMATCH"),
        (request.authority_class in set(map(str, admission.get("eligible_authority_classes", ()))), "AUTHORITY_CLASS_NOT_ADMITTED"),
        (request.packet_class in set(map(str, admission.get("eligible_packet_classes", ()))), "PACKET_CLASS_NOT_ADMITTED"),
        (request.side_effect_class in set(map(str, admission.get("allowed_side_effect_classes", ()))), "SIDE_EFFECT_CLASS_NOT_ADMITTED"),
    )
    for passed, reason in exact_admission_checks:
        if not passed:
            return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", reason, (reason,))

    # EXECUTOR.
    if not request.executor_binding_id or executor_binding is None:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "EXECUTOR_UNKNOWN_OR_INACTIVE", ("EXECUTOR_UNKNOWN_OR_INACTIVE",))
    if executor_binding.get("binding_id") != request.executor_binding_id or admission.get("executor_binding_id") != request.executor_binding_id:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "EXECUTOR_BINDING_MISMATCH", ("EXECUTOR_BINDING_MISMATCH",))
    if executor_binding.get("status") != "ACTIVE":
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "EXECUTOR_UNKNOWN_OR_INACTIVE", ("EXECUTOR_UNKNOWN_OR_INACTIVE",))
    if executor_binding.get("merge") is not False or executor_binding.get("force_push") is not False or executor_binding.get("history_rewrite") is not False:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "EXECUTOR_FORBIDDEN_CAPABILITY", ("EXECUTOR_FORBIDDEN_CAPABILITY",))
    if executor_binding.get("irreversible_external_side_effects") is not False:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "EXECUTOR_IRREVERSIBLE_SIDE_EFFECT", ("EXECUTOR_IRREVERSIBLE_SIDE_EFFECT",))

    # ACTION / SIDE EFFECT / WRITE DOMAIN.
    action_entry = _registry_entry(action_registry, request.action)
    if action_entry is None or action_entry.get("allowed") is not True:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "ACTION_UNKNOWN_OR_DENIED", ("ACTION_UNKNOWN_OR_DENIED",))
    if action_entry.get("side_effect_class") != request.side_effect_class:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "SIDE_EFFECT_CLASS_MISMATCH", ("SIDE_EFFECT_CLASS_MISMATCH",))
    if request.action not in set(map(str, executor_binding.get("action_classes", ()))):
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "EXECUTOR_ACTION_UNSUPPORTED", ("EXECUTOR_ACTION_UNSUPPORTED",))
    if request.action in {"WRITE_FILE", "GIT_COMMIT", "PUSH_BRANCH"}:
        if not request.write_domain or not request.write_domain_declared:
            return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "WRITE_DOMAIN_UNKNOWN_OR_DENIED", ("WRITE_DOMAIN_UNKNOWN_OR_DENIED",))
        if not request.semantic_owner or not request.semantic_owner_match:
            return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "SEMANTIC_OWNER_MISMATCH", ("SEMANTIC_OWNER_MISMATCH",))
        if admission.get("write_domain_rule") != "PACKET_DECLARED_WRITE_DOMAIN_AND_SEMANTIC_OWNER_ONLY":
            return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "WRITE_DOMAIN_RULE_MISMATCH", ("WRITE_DOMAIN_RULE_MISMATCH",))
        if admission.get("semantic_owner_rule") != "EXACT_PACKET_SEMANTIC_OWNER_ONLY":
            return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "DENY", "SEMANTIC_OWNER_RULE_MISMATCH", ("SEMANTIC_OWNER_RULE_MISMATCH",))

    # PREREQUISITE / DEPENDENCY.
    if not request.prerequisites_pass:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "PARK", "PREREQUISITE_UNSATISFIED", ("PREREQUISITE_UNSATISFIED",))
    if not request.dependency_frontier_current:
        return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "PARK", "DEPENDENCY_FRONTIER_STALE", ("DEPENDENCY_FRONTIER_STALE",))

    return PersistentAuthorityView(request.programme_id, request.packet_id, request.request_id, "ALLOW", "RUNNABLE", ("RUNNABLE",))


def reconcile_persistent_requests(
    requests: Iterable[PersistentWorkRequest],
    *,
    snapshot_id: str,
    admissions: Mapping[str, Mapping[str, Any]],
    policy: Mapping[str, Any],
    executor_bindings: Mapping[str, Mapping[str, Any]],
    action_registry: Mapping[str, Any],
    quiescence_mode: str,
    fencing_generation: int,
) -> PersistentReconciliationResult:
    if fencing_generation < 1:
        raise ValueError("FENCING_GENERATION_MUST_BE_POSITIVE")

    views: list[PersistentAuthorityView] = []
    dispatches: list[PersistentDispatchProposal] = []
    for request in sorted(tuple(requests), key=lambda row: (row.priority, row.programme_id, row.packet_id, row.action, row.request_id)):
        admission = admissions.get(request.programme_id)
        binding = executor_bindings.get(request.executor_binding_id or "")
        view = derive_authority_view(
            request,
            admission=admission,
            policy=policy,
            executor_binding=binding,
            action_registry=action_registry,
            quiescence_mode=quiescence_mode,
        )
        views.append(view)
        if view.decision == "ALLOW":
            dispatches.append(
                PersistentDispatchProposal(
                    programme_id=request.programme_id,
                    packet_id=request.packet_id,
                    request_id=request.request_id,
                    authority_view_id=view.view_id,
                    executor_identity=str(binding["executor_identity"]),
                    action=request.action,
                    write_domain=request.write_domain,
                    semantic_owner=request.semantic_owner,
                    fencing_generation=fencing_generation,
                )
            )
    return PersistentReconciliationResult(snapshot_id=snapshot_id, views=tuple(views), dispatches=tuple(dispatches))


def route_failure_to_owner(programme_id: str, packet_id: str, reason: str) -> Mapping[str, str]:
    return {
        "programme_id": programme_id,
        "packet_id": packet_id,
        "reason": reason,
        "route": "EXISTING_PROGRAMME_REPAIR_OWNER",
        "cers_remediation_authority": "NONE",
    }

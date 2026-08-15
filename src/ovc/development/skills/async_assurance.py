from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ovc.development.identity import canonical_sha256

AA0_BACKGROUND_REUSABLE = "AA0_BACKGROUND_REUSABLE"
AA1_PROSPECTIVE_TREE_BOUND = "AA1_PROSPECTIVE_TREE_BOUND"
AA2_MATERIALISATION_EDGE = "AA2_MATERIALISATION_EDGE"
AA3_POST_WRITE_EQUIVALENCE = "AA3_POST_WRITE_EQUIVALENCE"
ASSURANCE_CLASSES = {
    AA0_BACKGROUND_REUSABLE,
    AA1_PROSPECTIVE_TREE_BOUND,
    AA2_MATERIALISATION_EDGE,
    AA3_POST_WRITE_EQUIVALENCE,
}
REUSE_IF_DEPENDENCIES_UNCHANGED = "REUSE_IF_DEPENDENCIES_UNCHANGED"
NO_REUSE = "NO_REUSE"
FUTURE_STATES = {
    "CREATED", "RUNNING", "PASS", "FAIL_CORRECTABLE", "FAIL_BLOCKING",
    "STALE", "CANCELLED", "SUPERSEDED", "NOT_EVALUABLE",
}
INTENT_STATES = {
    "PREPARED", "WAITING_ASSURANCE", "WAITING_PREDECESSOR", "WAITING_CURRENTNESS",
    "WAITING_OPERATOR", "WAITING_LEASE", "MATERIALISATION_READY", "CONSUMED",
    "BLOCKED", "CANCELLED", "SUPERSEDED",
}
REQUIRED_READINESS_KEYS = (
    "OWNER_AUTHORITY_CURRENT",
    "PROGRAMME_STATE_POINTER_CONSISTENT",
    "QA_PASS",
    "NO_UNRESOLVED_WARNING_OR_REVIEW",
    "CURRENT_GRT_INTEGRATION_ASSURANCE",
    "EXPECTED_PREDECESSOR_CURRENT",
    "SECURITY_ALLOW",
    "SIQ_READY",
    "LEASE_READY",
)
IRREVERSIBLE_SPECULATIVE_ACTIONS = {
    "PROVIDER_INTAKE", "PUBLICATION", "EXTERNAL_DURABLE_PROGRAMME_WRITE",
    "OPERATOR_RESERVED_ACTION", "PHYSICAL_MATERIALISATION", "CANONICAL_PUBLICATION",
    "AGENT_WRITE",
}
CONTROLLER_IDENTITY = "DSAI_VIT_PHYSICAL_CONTROLLER"


def normalize_assurance_class(assurance_class: str | None, reuse_class: str | None) -> tuple[str, str]:
    normalized_class = assurance_class if assurance_class in ASSURANCE_CLASSES else AA2_MATERIALISATION_EDGE
    normalized_reuse = reuse_class if reuse_class in {REUSE_IF_DEPENDENCIES_UNCHANGED, NO_REUSE} else NO_REUSE
    if normalized_class in {AA2_MATERIALISATION_EDGE, AA3_POST_WRITE_EQUIVALENCE}:
        normalized_reuse = NO_REUSE
    return normalized_class, normalized_reuse


@dataclass(frozen=True)
class AssuranceFuture:
    programme_id: str
    packet_id: str
    payload_id: str
    assurance_profile_id: str
    candidate_commit: str
    provider_adapter_id: str
    workflow_name: str
    run_id: str
    check_name: str
    assurance_class: str = AA2_MATERIALISATION_EDGE
    reuse_class: str = NO_REUSE
    dependency_scope: tuple[str, ...] = ()
    vit_generation_id: str | None = None
    tree_id: str | None = None
    state: str = "CREATED"
    conclusion: str | None = None
    evidence_refs: tuple[str, ...] = ()
    superseded_by: str | None = None

    def __post_init__(self) -> None:
        klass, reuse = normalize_assurance_class(self.assurance_class, self.reuse_class)
        object.__setattr__(self, "assurance_class", klass)
        object.__setattr__(self, "reuse_class", reuse)
        object.__setattr__(self, "dependency_scope", tuple(sorted(set(self.dependency_scope))))
        if self.state not in FUTURE_STATES:
            raise ValueError("unknown AssuranceFuture state")
        for value in (
            self.programme_id, self.packet_id, self.payload_id, self.assurance_profile_id,
            self.candidate_commit, self.provider_adapter_id, self.workflow_name, self.run_id,
            self.check_name,
        ):
            if not value:
                raise ValueError("AssuranceFuture identity fields are required")

    @property
    def future_id(self) -> str:
        logical = {
            "programme_id": self.programme_id,
            "packet_id": self.packet_id,
            "payload_id": self.payload_id,
            "vit_generation_id": self.vit_generation_id,
            "assurance_profile_id": self.assurance_profile_id,
            "assurance_class": self.assurance_class,
            "reuse_class": self.reuse_class,
            "dependency_scope": self.dependency_scope,
            "candidate_commit": self.candidate_commit,
            "tree_id": self.tree_id,
            "provider_adapter_id": self.provider_adapter_id,
            "workflow_name": self.workflow_name,
            "run_id": self.run_id,
            "check_name": self.check_name,
        }
        return canonical_sha256(logical, role="OVC_DSAI3V_ASSURANCE_FUTURE")

    def to_record(self) -> dict[str, Any]:
        return {"schema": "ovc-dsai3v-assurance-future/v1", **asdict(self), "assurance_future_id": self.future_id}


@dataclass(frozen=True)
class AssuranceCompletionSignal:
    future_id: str
    provider_adapter_id: str
    repository: str
    candidate_commit: str
    workflow_name: str
    run_id: str
    check_name: str
    conclusion: str
    observed_at: str

    @property
    def signal_id(self) -> str:
        return canonical_sha256(asdict(self), role="OVC_DSAI3V_ASSURANCE_COMPLETION_SIGNAL")

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": "ovc-dsai3v-assurance-completion-signal/v1",
            **asdict(self),
            "signal_id": self.signal_id,
            "authority_effect": "NONE",
        }


@dataclass(frozen=True)
class RequiredAssuranceSet:
    programme_id: str
    packet_id: str
    version: str
    required_future_ids: tuple[str, ...]
    allowed_terminal_states: tuple[str, ...] = ("PASS",)

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_future_ids", tuple(sorted(set(self.required_future_ids))))
        object.__setattr__(self, "allowed_terminal_states", tuple(sorted(set(self.allowed_terminal_states))))
        if not self.required_future_ids:
            raise ValueError("RequiredAssuranceSet cannot be empty")

    @property
    def assurance_set_id(self) -> str:
        return canonical_sha256(asdict(self), role="OVC_DSAI3V_REQUIRED_ASSURANCE_SET")

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": "ovc-dsai3v-required-assurance-set/v1",
            **asdict(self),
            "required_assurance_set_id": self.assurance_set_id,
        }


@dataclass(frozen=True)
class ConditionalMaterialisationIntent:
    programme_id: str
    packet_id: str
    payload_id: str
    vit_generation_id: str
    train_generation_id: str
    expected_predecessor_commit: str
    expected_predecessor_tree: str
    expected_result_tree: str
    authority_manifest_id: str
    required_assurance_set_id: str
    materialisation_profile: str
    gate_class: str
    operator_required: bool = False
    state: str = "PREPARED"
    supersedes: str | None = None
    superseded_by: str | None = None

    def __post_init__(self) -> None:
        if self.state not in INTENT_STATES:
            raise ValueError("unknown materialisation intent state")

    @property
    def intent_id(self) -> str:
        logical = {k: v for k, v in asdict(self).items() if k not in {"state", "superseded_by"}}
        return canonical_sha256(logical, role="OVC_DSAI3V_CONDITIONAL_MATERIALISATION_INTENT")

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": "ovc-dsai3v-conditional-materialisation-intent/v1",
            **asdict(self),
            "materialisation_intent_id": self.intent_id,
            "action": "REQUEST_SERIALIZED_SQUASH_MATERIALISATION",
        }


@dataclass(frozen=True)
class AssuranceWakeSubscription:
    provider_adapter_id: str
    future_ids: tuple[str, ...]
    intent_ids: tuple[str, ...]
    controller_identity: str = CONTROLLER_IDENTITY
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        object.__setattr__(self, "future_ids", tuple(sorted(set(self.future_ids))))
        object.__setattr__(self, "intent_ids", tuple(sorted(set(self.intent_ids))))
        if self.controller_identity != CONTROLLER_IDENTITY:
            raise ValueError("new controller identity is not authorized")

    @property
    def subscription_id(self) -> str:
        return canonical_sha256(asdict(self), role="OVC_DSAI3V_ASSURANCE_WAKE_SUBSCRIPTION")


@dataclass(frozen=True)
class MaterialisationWakeRequest:
    intent_id: str
    controller_identity: str = CONTROLLER_IDENTITY
    action: str = "REQUEST_SERIALIZED_SQUASH_MATERIALISATION"
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.controller_identity != CONTROLLER_IDENTITY:
            raise ValueError("wake request may target only the existing DSAI controller")

    @property
    def request_id(self) -> str:
        return canonical_sha256(asdict(self), role="OVC_DSAI3V_MATERIALISATION_WAKE_REQUEST")


def _signal_state(conclusion: str) -> str:
    value = conclusion.upper()
    if value == "SUCCESS":
        return "PASS"
    if value in {"CANCELLED", "SKIPPED"}:
        return "CANCELLED"
    if value in {"FAILURE", "TIMED_OUT", "ACTION_REQUIRED"}:
        return "FAIL_CORRECTABLE"
    return "NOT_EVALUABLE"


def apply_completion_signal(future: AssuranceFuture, signal: AssuranceCompletionSignal) -> AssuranceFuture:
    if signal.future_id != future.future_id:
        raise ValueError("signal/future identity mismatch")
    exact = (
        signal.provider_adapter_id == future.provider_adapter_id
        and signal.candidate_commit == future.candidate_commit
        and signal.workflow_name == future.workflow_name
        and signal.run_id == future.run_id
        and signal.check_name == future.check_name
    )
    if not exact:
        raise ValueError("signal exact binding mismatch")
    if signal.signal_id in future.evidence_refs:
        return future
    next_state = _signal_state(signal.conclusion)
    if (
        future.state in {"PASS", "CANCELLED", "FAIL_CORRECTABLE", "FAIL_BLOCKING", "NOT_EVALUABLE"}
        and future.conclusion != signal.conclusion
    ):
        raise ValueError("conflicting terminal assurance signal")
    return replace(
        future,
        state=next_state,
        conclusion=signal.conclusion,
        evidence_refs=tuple(sorted(set(future.evidence_refs + (signal.signal_id,)))),
    )


def required_assurance_satisfied(
    assurance_set: RequiredAssuranceSet,
    futures: Mapping[str, AssuranceFuture],
) -> bool:
    for future_id in assurance_set.required_future_ids:
        future = futures.get(future_id)
        if future is None or future.state not in assurance_set.allowed_terminal_states:
            return False
        if future.state in {"STALE", "SUPERSEDED"} or future.superseded_by:
            return False
    return True


def evaluate_materialisation_intent(
    intent: ConditionalMaterialisationIntent,
    assurance_set: RequiredAssuranceSet,
    futures: Mapping[str, AssuranceFuture],
    readiness: Mapping[str, bool],
    *,
    operator_decision_durable: bool = False,
) -> tuple[ConditionalMaterialisationIntent, MaterialisationWakeRequest | None]:
    if intent.required_assurance_set_id != assurance_set.assurance_set_id:
        return replace(intent, state="SUPERSEDED"), None
    if intent.operator_required and not operator_decision_durable:
        return replace(intent, state="WAITING_OPERATOR"), None
    if not required_assurance_satisfied(assurance_set, futures):
        return replace(intent, state="WAITING_ASSURANCE"), None
    missing = [key for key in REQUIRED_READINESS_KEYS if readiness.get(key) is not True]
    if "EXPECTED_PREDECESSOR_CURRENT" in missing:
        return replace(intent, state="WAITING_PREDECESSOR"), None
    if "SIQ_READY" in missing or "LEASE_READY" in missing:
        return replace(intent, state="WAITING_LEASE"), None
    if missing:
        return replace(intent, state="WAITING_CURRENTNESS"), None
    ready = replace(intent, state="MATERIALISATION_READY")
    return ready, MaterialisationWakeRequest(ready.intent_id)


def supersede_intent_for_assurance_set(
    intent: ConditionalMaterialisationIntent,
    new_assurance_set_id: str,
) -> tuple[ConditionalMaterialisationIntent, ConditionalMaterialisationIntent]:
    new_intent = replace(
        intent,
        required_assurance_set_id=new_assurance_set_id,
        state="PREPARED",
        supersedes=intent.intent_id,
        superseded_by=None,
    )
    old = replace(intent, state="SUPERSEDED", superseded_by=new_intent.intent_id)
    return old, new_intent


def should_continue_development(future: AssuranceFuture) -> bool:
    return future.state != "FAIL_BLOCKING"


def speculative_action_allowed(
    action: str,
    *,
    predecessor_authoritative: bool,
    own_authority_current: bool = True,
) -> bool:
    if not own_authority_current:
        return False
    if action.upper() in IRREVERSIBLE_SPECULATIVE_ACTIONS and not predecessor_authoritative:
        return False
    return True


def selective_descendant_invalidation(
    descendants: Sequence[Mapping[str, Any]],
    changed_dependency_ids: Iterable[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    changed = set(changed_dependency_ids)
    invalidated: list[str] = []
    preserved: list[str] = []
    for row in descendants:
        packet_id = str(row["packet_id"])
        dependencies = set(str(value) for value in row.get("dependency_ids", ()))
        (invalidated if dependencies & changed else preserved).append(packet_id)
    return tuple(sorted(invalidated)), tuple(sorted(preserved))


def promote_speculative_successor(
    state: str,
    *,
    expected_predecessor_tree: str,
    observed_predecessor_tree: str,
    dependencies_valid: bool,
) -> str:
    if state != "SPECULATIVE_RUNNING":
        return state
    if dependencies_valid and expected_predecessor_tree == observed_predecessor_tree:
        return "AUTHORITATIVE_RUNNING"
    return "SPECULATIVE_RUNNING"


def reuse_after_frontier_change(
    future: AssuranceFuture,
    changed_dependency_ids: Iterable[str],
) -> AssuranceFuture:
    if future.state != "PASS":
        return future
    changed = set(changed_dependency_ids)
    if (
        future.assurance_class == AA0_BACKGROUND_REUSABLE
        and future.reuse_class == REUSE_IF_DEPENDENCIES_UNCHANGED
        and not (set(future.dependency_scope) & changed)
    ):
        return future
    return replace(future, state="STALE")


class AsyncAssuranceStore:
    """Durable state shared by event-driven and reconciliation paths."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _write(self, kind: str, record_id: str, record: Mapping[str, Any]) -> Path:
        path = self.root / f"{kind}-{record_id}.json"
        path.write_text(json.dumps(dict(record), sort_keys=True, separators=(",", ":")), encoding="utf-8")
        return path

    def put_future(self, future: AssuranceFuture) -> Path:
        return self._write("future", future.future_id, future.to_record())

    def put_signal(self, signal: AssuranceCompletionSignal) -> Path:
        path = self.root / f"signal-{signal.signal_id}.json"
        encoded = json.dumps(signal.to_record(), sort_keys=True, separators=(",", ":"))
        if path.exists() and path.read_text(encoding="utf-8") != encoded:
            raise ValueError("ASSURANCE_SIGNAL_IDENTITY_CONFLICT")
        if not path.exists():
            path.write_text(encoded, encoding="utf-8")
        return path

    def put_intent(self, intent: ConditionalMaterialisationIntent) -> Path:
        return self._write("intent", intent.intent_id, intent.to_record())

    def get_future(self, future_id: str) -> AssuranceFuture:
        raw = json.loads((self.root / f"future-{future_id}.json").read_text(encoding="utf-8"))
        fields = {k: raw[k] for k in AssuranceFuture.__dataclass_fields__}
        fields["dependency_scope"] = tuple(fields.get("dependency_scope") or ())
        fields["evidence_refs"] = tuple(fields.get("evidence_refs") or ())
        future = AssuranceFuture(**fields)
        if future.future_id != future_id:
            raise ValueError("ASSURANCE_STORE_IDENTITY_MISMATCH")
        return future

    def get_intent(self, intent_id: str) -> ConditionalMaterialisationIntent:
        raw = json.loads((self.root / f"intent-{intent_id}.json").read_text(encoding="utf-8"))
        fields = {k: raw[k] for k in ConditionalMaterialisationIntent.__dataclass_fields__}
        intent = ConditionalMaterialisationIntent(**fields)
        if intent.intent_id != intent_id:
            raise ValueError("ASSURANCE_STORE_IDENTITY_MISMATCH")
        return intent

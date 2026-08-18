from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from ovc.development.identity import canonical_sha256, normalize_relative_path
from .model import DispatchIdentity, DispatchTransaction, QuiescenceControl, SupervisorLease, WorkerOwnership, canonical_id

PROGRAMME_ID = "OVC-DSAI3V-CERS-CONFORMANCE-v0.1"
PACKET_ID = "CERS-WP6"
PACKET_CLASS = "LOW_RISK_IMPLEMENTATION"
SEMANTIC_OWNER = "CERS"
EXECUTOR_ID = "OVC-SKILL-030@0.1.0+sha256:62809d0f5f1d4298fa916766912d4bec7b5a8bf7712f7382d448137f6f12f130|PACKET_EXECUTION|windows-local-python311"
LIVE_ACTIONS = ("WRITE_FILE", "GIT_COMMIT", "PUSH_BRANCH")
LIVE_WRITE_PATHS = (
    "registries/development/skills/cers/CERS_ACTION_SIDE_EFFECT_REGISTRY_v0_2.json",
    "src/ovc/development/skills/cers/live.py",
    "tests/development_skills/cers/test_cers_wp6_live_pilot.py",
    "docs/releases/development-skills-v0-3/cers-conformance/wp6/CERS_WP6_LIVE_PILOT_RUN_v0_1.json",
)
LIVE_WORK_MANIFEST = {
    "programme_id": PROGRAMME_ID,
    "packet_id": PACKET_ID,
    "packet_class": PACKET_CLASS,
    "semantic_owner": SEMANTIC_OWNER,
    "action": "WRITE_FILE",
    "write_paths": list(LIVE_WRITE_PATHS),
}
EXPECTED_WORK_ID = canonical_id(LIVE_WORK_MANIFEST)
FORBIDDEN_ACTIONS = {
    "MERGE", "FORCE_PUSH", "HISTORY_REWRITE", "DIRECT_MAIN_WRITE", "VALIDATION_READ",
    "SCIENTIFIC_PROMOTION", "CANONICAL_PUBLICATION", "R2_PUBLICATION", "PROBABILITY",
    "RISK", "EXPOSURE", "TRADING", "EXECUTION",
}


class LivePilotViolation(PermissionError):
    pass


@dataclass(frozen=True)
class LivePilotCheckpoint:
    fencing_generation: int
    open_dispatch_ids: tuple[str, ...]
    last_reconciliation_id: str | None
    event_watermarks: Mapping[str, int]
    chat_dependency_count: int
    quiescence_mode: str
    quiescence_source: str


def _decision(payload: Mapping[str, Any]) -> dict[str, Any]:
    logical = dict(payload)
    return {
        "schema": "ovc-cers-live-action-decision/v1",
        **logical,
        "decision_id": canonical_sha256(logical, role="CERS_LIVE_ACTION_DECISION"),
        "authority_effect": "NONE",
    }


def validate_background_assurance_witness(witness: Mapping[str, Any]) -> dict[str, Any]:
    workflows = list(witness.get("workflows", ()))
    running = [row for row in workflows if str(row.get("status", "")).lower() == "in_progress"]
    if not running:
        raise LivePilotViolation("BACKGROUND_ASSURANCE_NOT_RUNNING")
    if witness.get("caller_absent") is not True:
        raise LivePilotViolation("CALLER_ABSENCE_NOT_OBSERVED")
    logical = {
        "repository": str(witness.get("repository", "")),
        "observed_head": str(witness.get("observed_head", "")),
        "running_workflows": [
            {"name": str(row.get("name", "")), "run_id": int(row.get("run_id", 0)), "run_number": int(row.get("run_number", 0)), "status": "in_progress"}
            for row in running
        ],
        "caller_absent": True,
    }
    return {"schema": "ovc-cers-background-assurance-witness/v1", **logical, "witness_id": canonical_sha256(logical, role="CERS_BACKGROUND_ASSURANCE_WITNESS"), "status": "PASS"}


class LivePilotCoordinator:
    """Bounded WP6 coordinator consuming, never granting, operator-approved authority."""

    def __init__(self, authority: Mapping[str, Any], freeze: Mapping[str, Any]) -> None:
        self.authority = dict(authority)
        self.freeze = dict(freeze)
        self._validate_binding()
        self.current_generation = 0
        self.current_lease: SupervisorLease | None = None
        self.quiescence = QuiescenceControl("RUN", "CERS_WP6_PILOT")
        self.transactions: dict[str, DispatchTransaction] = {}
        self.workers: dict[str, WorkerOwnership] = {}
        self.quarantine_reason: str | None = None
        self.last_reconciliation_id: str | None = None

    def _validate_binding(self) -> None:
        a = self.authority; f = self.freeze
        if a.get("approved") is not True or a.get("effective") is not True:
            raise LivePilotViolation("LIVE_DISPATCH_AUTHORITY_INACTIVE")
        if str(a.get("programme_id")) != PROGRAMME_ID:
            raise LivePilotViolation("PROGRAMME_NOT_AUTHORISED")
        scope = a.get("scope", {})
        if list(scope.get("programme_allowlist", ())) != [PROGRAMME_ID]: raise LivePilotViolation("PROGRAMME_ALLOWLIST_DRIFT")
        if list(scope.get("packet_allowlist", ())) != [PACKET_ID]: raise LivePilotViolation("PACKET_ALLOWLIST_DRIFT")
        if list(scope.get("packet_class_allowlist", ())) != [PACKET_CLASS]: raise LivePilotViolation("PACKET_CLASS_ALLOWLIST_DRIFT")
        if int(scope.get("worker_concurrency", 0)) != 1 or int(scope.get("max_speculative_depth", 0)) != 1: raise LivePilotViolation("LIVE_PILOT_CAP_DRIFT")
        if str(a.get("executor", {}).get("executor_identity")) != EXECUTOR_ID: raise LivePilotViolation("EXECUTOR_IDENTITY_MISMATCH")
        if f.get("status") != "FROZEN_PRE_EXECUTION": raise LivePilotViolation("PILOT_BOUNDS_NOT_FROZEN")
        if str(f.get("programme_id")) != PROGRAMME_ID or str(f.get("packet_id")) != PACKET_ID: raise LivePilotViolation("FREEZE_SCOPE_MISMATCH")
        if str(f.get("executor", {}).get("executor_identity")) != EXECUTOR_ID: raise LivePilotViolation("FREEZE_EXECUTOR_MISMATCH")
        if list(f.get("action_classes", ())) != list(LIVE_ACTIONS): raise LivePilotViolation("FREEZE_ACTION_CLASS_DRIFT")
        if f.get("direct_main_mutation") is not False or f.get("parallel_physical_merge") is not False: raise LivePilotViolation("PHYSICAL_MAIN_BOUNDARY_DRIFT")
        if f.get("force_push") is not False or f.get("history_rewrite") is not False: raise LivePilotViolation("HISTORY_SAFETY_BOUNDARY_DRIFT")
        frozen_paths = {normalize_relative_path(str(path)) for path in f.get("exact_write_paths", ())}
        if not set(LIVE_WRITE_PATHS).issubset(frozen_paths): raise LivePilotViolation("LIVE_WORK_PATH_NOT_FROZEN")

    @property
    def branch(self) -> str: return str(self.freeze["branch"])

    @property
    def exact_write_paths(self) -> frozenset[str]: return frozenset(normalize_relative_path(str(path)) for path in self.freeze.get("exact_write_paths", ()))

    def acquire_lease(self, holder_identity: str = EXECUTOR_ID) -> SupervisorLease:
        if self.quarantine_reason: raise LivePilotViolation("PILOT_QUARANTINED")
        self.current_generation += 1
        self.current_lease = SupervisorLease(scope=f"{PROGRAMME_ID}:{PACKET_ID}", holder_identity=holder_identity, fencing_generation=self.current_generation)
        return self.current_lease

    def validate_lease(self, lease: SupervisorLease) -> None:
        current = self.current_lease
        if not current or not current.active or lease.lease_id != current.lease_id or lease.fencing_generation != self.current_generation:
            raise LivePilotViolation("STALE_FENCE")

    def authorize_action(self, *, action: str, branch: str, semantic_owner: str, path: str | None = None) -> dict[str, Any]:
        action = str(action).upper(); reasons: list[str] = []
        if action in FORBIDDEN_ACTIONS or action not in LIVE_ACTIONS: reasons.append("ACTION_NOT_AUTHORISED")
        if branch != self.branch or branch == "main": reasons.append("BRANCH_SCOPE_DENIED")
        if semantic_owner != SEMANTIC_OWNER: reasons.append("SEMANTIC_OWNERSHIP_DENIED")
        normalized: str | None = None
        if action == "WRITE_FILE":
            if path is None: reasons.append("WRITE_PATH_REQUIRED")
            else:
                try: normalized = normalize_relative_path(path)
                except (ValueError, OSError): reasons.append("UNSAFE_WRITE_PATH")
                if normalized is not None and normalized not in self.exact_write_paths: reasons.append("WRITE_PATH_OUT_OF_FROZEN_SCOPE")
        elif path is not None: reasons.append("NON_FILE_ACTION_PATH_MUST_BE_ABSENT")
        payload = {"programme_id": PROGRAMME_ID, "packet_id": PACKET_ID, "action": action, "branch": branch, "semantic_owner": semantic_owner, "normalized_path": normalized, "decision": "DENY" if reasons else "ALLOW", "reason_codes": sorted(set(reasons))}
        result = _decision(payload)
        if reasons: raise LivePilotViolation(";".join(sorted(set(reasons))))
        return result

    def start(self, identity: DispatchIdentity, lease: SupervisorLease, *, packet_class: str, first_write_path: str, background_assurance: Mapping[str, Any]) -> DispatchTransaction:
        self.validate_lease(lease)
        if self.quiescence.blocks_new_dispatch: raise LivePilotViolation("QUIESCENCE_BLOCKS_NEW_DISPATCH")
        if self.quarantine_reason: raise LivePilotViolation("PILOT_QUARANTINED")
        if identity.programme_id != PROGRAMME_ID or identity.packet_id != PACKET_ID: raise LivePilotViolation("DISPATCH_SCOPE_MISMATCH")
        if packet_class != PACKET_CLASS: raise LivePilotViolation("PACKET_CLASS_NOT_AUTHORISED")
        if identity.executor_id != EXECUTOR_ID: raise LivePilotViolation("EXECUTOR_IDENTITY_MISMATCH")
        if identity.action != "WRITE_FILE": raise LivePilotViolation("DISPATCH_ACTION_MISMATCH")
        if identity.work_id != EXPECTED_WORK_ID: raise LivePilotViolation("WORK_IDENTITY_MISMATCH")
        if identity.fencing_generation != lease.fencing_generation: raise LivePilotViolation("STALE_FENCE")
        if identity.dispatch_id in self.workers:
            self.quarantine_reason = "DUPLICATE_AUTHORITATIVE_START"; raise LivePilotViolation("DUPLICATE_AUTHORITATIVE_START")
        self.authorize_action(action=identity.action, branch=self.branch, semantic_owner=SEMANTIC_OWNER, path=first_write_path)
        validate_background_assurance_witness(background_assurance)
        self.transactions[identity.dispatch_id] = DispatchTransaction(identity.dispatch_id, "INTENT_PERSISTED", lease.fencing_generation)
        worker = WorkerOwnership(dispatch_id=identity.dispatch_id, worker_run_id=f"cers-live-{identity.dispatch_id[:20]}", executor_id=EXECUTOR_ID, fencing_generation=lease.fencing_generation, heartbeat_sequence=1, authoritative=True)
        self.workers[identity.dispatch_id] = worker
        started = DispatchTransaction(identity.dispatch_id, "START_ACKNOWLEDGED", lease.fencing_generation, worker.worker_run_id)
        self.transactions[identity.dispatch_id] = started
        return started

    def heartbeat(self, dispatch_id: str, lease: SupervisorLease) -> WorkerOwnership:
        self.validate_lease(lease); worker = self.workers[dispatch_id]
        if worker.fencing_generation != lease.fencing_generation or not worker.authoritative: raise LivePilotViolation("STALE_WORKER_HEARTBEAT")
        worker = replace(worker, heartbeat_sequence=worker.heartbeat_sequence + 1); self.workers[dispatch_id] = worker; return worker

    def mark_unknown_start(self, identity: DispatchIdentity, lease: SupervisorLease) -> DispatchTransaction:
        self.validate_lease(lease); unknown = DispatchTransaction(identity.dispatch_id, "DISPATCH_UNKNOWN", lease.fencing_generation, reason="UNKNOWN_START_STATE"); self.transactions[identity.dispatch_id] = unknown; return unknown

    def reconcile_unknown(self, dispatch_id: str, observed_worker: WorkerOwnership | None) -> DispatchTransaction:
        current = self.transactions[dispatch_id]
        if current.phase != "DISPATCH_UNKNOWN": return current
        logical = {"dispatch_id": dispatch_id, "observed_worker_run_id": observed_worker.worker_run_id if observed_worker else None, "observed_fencing_generation": observed_worker.fencing_generation if observed_worker else None}
        self.last_reconciliation_id = canonical_sha256(logical, role="CERS_UNKNOWN_START_RECONCILIATION")
        if observed_worker is None: return current
        if observed_worker.fencing_generation != self.current_generation or not observed_worker.authoritative: raise LivePilotViolation("STALE_WORKER_OBSERVED_DURING_RECONCILIATION")
        self.workers[dispatch_id] = observed_worker
        resolved = DispatchTransaction(dispatch_id, "START_ACKNOWLEDGED", observed_worker.fencing_generation, observed_worker.worker_run_id, reason="RECOVERED_EXISTING_START_NO_REDISPATCH")
        self.transactions[dispatch_id] = resolved; return resolved

    def complete(self, dispatch_id: str, lease: SupervisorLease, *, success: bool = True) -> DispatchTransaction:
        self.validate_lease(lease); worker = self.workers[dispatch_id]
        if worker.fencing_generation != lease.fencing_generation or not worker.authoritative: raise LivePilotViolation("STALE_WORKER_AUTHORITATIVE_COMPLETION")
        result = DispatchTransaction(dispatch_id, "COMPLETED" if success else "FAILED", lease.fencing_generation, worker.worker_run_id); self.transactions[dispatch_id] = result; return result

    def disable_new_dispatch(self) -> None: self.quiescence = QuiescenceControl("DISABLE_NEW_DISPATCH", "CERS_WP6_ROLLBACK_OR_POST_PILOT_QUIESCENCE")

    def checkpoint(self) -> LivePilotCheckpoint:
        open_ids = tuple(sorted(dispatch_id for dispatch_id, tx in self.transactions.items() if tx.phase not in {"COMPLETED", "FAILED", "CANCELLED"}))
        return LivePilotCheckpoint(fencing_generation=self.current_generation, open_dispatch_ids=open_ids, last_reconciliation_id=self.last_reconciliation_id, event_watermarks={}, chat_dependency_count=0, quiescence_mode=self.quiescence.mode, quiescence_source=self.quiescence.source)

    @classmethod
    def restore(cls, authority: Mapping[str, Any], freeze: Mapping[str, Any], checkpoint: LivePilotCheckpoint) -> "LivePilotCoordinator":
        if checkpoint.chat_dependency_count != 0: raise LivePilotViolation("CHAT_DEPENDENT_RESTART")
        restored = cls(authority, freeze); restored.current_generation = checkpoint.fencing_generation; restored.last_reconciliation_id = checkpoint.last_reconciliation_id; restored.quiescence = QuiescenceControl(checkpoint.quiescence_mode, checkpoint.quiescence_source); return restored

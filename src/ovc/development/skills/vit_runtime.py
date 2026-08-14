from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import ContinuousExecutionMandate, DevelopmentLane, VitContractError


@dataclass(frozen=True)
class RecoveryState:
    state: str
    blocker_codes: tuple[str, ...] = ()
    open_action: str | None = None
    attempts: int = 0
    recovery_budget: int = 3
    wake_subscriptions: tuple[str, ...] = ()
    open_materialisation_transaction: str | None = None
    next_packet: str | None = None

    def __post_init__(self) -> None:
        if self.state not in {"RUNNING", "RECOVERING", "WAITING_OPERATOR_AUTHORITY", "BLOCKED", "QUARANTINED", "COMPLETED"}:
            raise VitContractError("unknown recovery state")
        if self.attempts < 0 or self.recovery_budget < 0:
            raise VitContractError("invalid recovery counters")

    @property
    def recovery_available(self) -> bool:
        return self.state == "RECOVERING" and self.attempts < self.recovery_budget


@dataclass(frozen=True)
class PersistentExecutionState:
    mandate: ContinuousExecutionMandate
    lane: DevelopmentLane
    recovery: RecoveryState
    schema_version: str = "persistent-execution-state/v0.1"

    @property
    def state_id(self) -> str:
        return canonical_sha256(asdict(self))


@dataclass(frozen=True)
class StateDrainageManifest:
    state_id: str
    mandate_id: str
    lane_id: str
    programme_id: str
    current_packet: str
    build_frontier: str
    payload_frontier: str | None
    vit_frontier: str | None
    materialisation_frontier: str | None
    recovery_state: str
    blocker_codes: tuple[str, ...]
    open_action: str | None
    recovery_attempts: int
    wake_subscriptions: tuple[str, ...]
    open_materialisation_transaction: str | None
    next_packet: str | None
    chat_dependency_count: int = 0

    @property
    def manifest_id(self) -> str:
        return canonical_sha256(asdict(self))


@dataclass(frozen=True)
class ContinuationDecision:
    action: str
    current_packet: str
    next_packet: str | None
    reason: str


class DurableExecutionStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, state: PersistentExecutionState) -> Path:
        path = self.root / f"{state.state_id}.json"
        payload = asdict(state)
        payload["state_id"] = state.state_id
        path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        return path

    def load(self, path: str | Path) -> PersistentExecutionState:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        mandate = ContinuousExecutionMandate(**raw["mandate"])
        lane = DevelopmentLane(**raw["lane"])
        recovery_raw: Mapping[str, Any] = raw["recovery"]
        recovery = RecoveryState(
            state=str(recovery_raw["state"]),
            blocker_codes=tuple(recovery_raw.get("blocker_codes", ())),
            open_action=recovery_raw.get("open_action"),
            attempts=int(recovery_raw.get("attempts", 0)),
            recovery_budget=int(recovery_raw.get("recovery_budget", 3)),
            wake_subscriptions=tuple(recovery_raw.get("wake_subscriptions", ())),
            open_materialisation_transaction=recovery_raw.get("open_materialisation_transaction"),
            next_packet=recovery_raw.get("next_packet"),
        )
        state = PersistentExecutionState(mandate, lane, recovery, raw.get("schema_version", "persistent-execution-state/v0.1"))
        expected = raw.get("state_id")
        if expected and expected != state.state_id:
            raise VitContractError("VIT_LEDGER_INTEGRITY_FAIL")
        return state


def drain_state(path: str | Path) -> StateDrainageManifest:
    """Fresh-process-safe reconstruction surface: the input path is the only state dependency."""
    store = DurableExecutionStore(Path(path).parent)
    state = store.load(path)
    return StateDrainageManifest(
        state_id=state.state_id,
        mandate_id=state.mandate.mandate_id,
        lane_id=state.lane.lane_id,
        programme_id=state.lane.programme_id,
        current_packet=state.lane.current_packet,
        build_frontier=state.lane.build_frontier,
        payload_frontier=state.lane.payload_frontier,
        vit_frontier=state.lane.vit_frontier,
        materialisation_frontier=state.lane.materialisation_frontier,
        recovery_state=state.recovery.state,
        blocker_codes=state.recovery.blocker_codes,
        open_action=state.recovery.open_action,
        recovery_attempts=state.recovery.attempts,
        wake_subscriptions=state.recovery.wake_subscriptions,
        open_materialisation_transaction=state.recovery.open_materialisation_transaction,
        next_packet=state.recovery.next_packet,
        chat_dependency_count=0,
    )


def recovery_transition(state: RecoveryState, result: str) -> RecoveryState:
    if state.state == "WAITING_OPERATOR_AUTHORITY":
        return state
    if result == "SUCCESS":
        return RecoveryState("RUNNING", next_packet=state.next_packet)
    if result == "AUTHORITY_REQUIRED":
        return RecoveryState("WAITING_OPERATOR_AUTHORITY", state.blocker_codes, "OPERATOR_DECISION", state.attempts, state.recovery_budget, state.wake_subscriptions, state.open_materialisation_transaction, state.next_packet)
    attempts = state.attempts + 1
    if attempts >= state.recovery_budget:
        return RecoveryState("BLOCKED", state.blocker_codes + ("RECOVERY_BUDGET_EXHAUSTED",), None, attempts, state.recovery_budget, state.wake_subscriptions, state.open_materialisation_transaction, state.next_packet)
    return RecoveryState("RECOVERING", state.blocker_codes, state.open_action, attempts, state.recovery_budget, state.wake_subscriptions, state.open_materialisation_transaction, state.next_packet)


def resolve_continuation(
    mandate: ContinuousExecutionMandate,
    *,
    current_packet: str,
    next_packet: str | None,
    prerequisites_pass: bool,
    next_authority_class: str = "AUTO_EXECUTABLE",
) -> ContinuationDecision:
    """Resolve the next lawful action without inventing packet or authority state."""
    if mandate.command == "HOLD":
        return ContinuationDecision("HOLD", current_packet, next_packet, "EXPLICIT_HOLD")
    if mandate.command in {"RUN_ONLY", "CONTINUE_ONLY"}:
        return ContinuationDecision("STOP", current_packet, next_packet, "ONLY_BOUNDARY_COMPLETE")
    if mandate.stop_boundary is not None and (
        current_packet == mandate.stop_boundary or next_packet == mandate.stop_boundary
    ):
        return ContinuationDecision("STOP", current_packet, next_packet, "EXPLICIT_UNTIL_BOUNDARY")
    if next_packet is None:
        return ContinuationDecision("STOP", current_packet, None, "PROGRAMME_TERMINAL")
    if next_authority_class != "AUTO_EXECUTABLE":
        return ContinuationDecision("WAITING_OPERATOR_AUTHORITY", current_packet, next_packet, "RESERVED_SUCCESSOR")
    if not prerequisites_pass:
        return ContinuationDecision("WAITING_PREREQUISITE", current_packet, next_packet, "PREREQUISITE_UNSATISFIED")
    return ContinuationDecision("START_SUCCESSOR", current_packet, next_packet, "CONTINUE_UNTIL_MANDATORY_STOP")

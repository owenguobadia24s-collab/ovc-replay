"""Fail-closed selected-class DGS cutover and writer-fencing contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


SELECTED_CLASS = "DSAI_VIT_RECEIPT_ONLY_V0_1"
INCUMBENT_ROUTE = "CERS_PES_EXACT_OLD_ROUTE"
SUCCESSOR_ROUTE = "DSAI_VIT_AND_VIT_QUALIFICATION_OWNER_LOCAL"
INCUMBENT_WRITER = "PES"
SUCCESSOR_WRITER = "VIT_QUALIFICATION_OWNER_LOCAL"
PHYSICAL_CONTROLLER = "DSAI_VIT_PHYSICAL_CONTROLLER"
PHYSICAL_GATEWAY = "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"
CUTOVER_GATE = "DIASI-G-DGS-CUTOVER-DRAIN"
CUTOVER_PHRASE = "OVC APPROVE DIASI-G-DGS-CUTOVER-DRAIN PASS"


class DiasCutoverError(RuntimeError):
    """Raised when a live transition could create an unfenced or unknown route."""


@dataclass(frozen=True)
class InFlightItem:
    item_id: str
    packet_class: str
    incumbent_generation: int
    disposition: str


@dataclass(frozen=True)
class CutoverState:
    selected_class: str
    intake: str
    route: str
    route_generation: int
    qualification_writer: str
    writer_generation: int
    old_route: str
    reference_assurance: str
    physical_controller: str = PHYSICAL_CONTROLLER
    physical_gateway: str = PHYSICAL_GATEWAY
    parallel_physical_writer: bool = False


def initial_state() -> CutoverState:
    return CutoverState(
        selected_class=SELECTED_CLASS,
        intake="OPEN_INCUMBENT",
        route=INCUMBENT_ROUTE,
        route_generation=1,
        qualification_writer=INCUMBENT_WRITER,
        writer_generation=1,
        old_route="ACTIVE",
        reference_assurance="COMPLETE_REFERENCE_ROUTE",
    )


def freeze_selected_intake(state: CutoverState, *, packet_class: str) -> CutoverState:
    if packet_class != SELECTED_CLASS or state.selected_class != SELECTED_CLASS:
        raise DiasCutoverError("DIASI_CUTOVER_GLOBAL_OR_WRONG_CLASS_FREEZE_DENIED")
    if state.intake != "OPEN_INCUMBENT" or state.route != INCUMBENT_ROUTE:
        raise DiasCutoverError("DIASI_CUTOVER_FREEZE_PRECONDITION_INVALID")
    return CutoverState(**{**state.__dict__, "intake": "FROZEN_EXACT_SELECTED_CLASS"})


def disposition_in_flight(
    state: CutoverState,
    items: Iterable[InFlightItem],
) -> tuple[InFlightItem, ...]:
    if state.intake != "FROZEN_EXACT_SELECTED_CLASS":
        raise DiasCutoverError("DIASI_CUTOVER_ENUMERATION_BEFORE_FREEZE")
    rows = tuple(items)
    allowed = {"COMPLETE_OLD", "MIGRATE_NEW", "QUARANTINE_BLOCK"}
    if any(item.packet_class != SELECTED_CLASS for item in rows):
        raise DiasCutoverError("DIASI_CUTOVER_IN_FLIGHT_SCOPE_ESCAPE")
    if any(item.incumbent_generation != 1 for item in rows):
        raise DiasCutoverError("DIASI_CUTOVER_IN_FLIGHT_GENERATION_UNKNOWN")
    if any(item.disposition not in allowed for item in rows):
        raise DiasCutoverError("DIASI_CUTOVER_IN_FLIGHT_DISPOSITION_UNKNOWN")
    if any(item.disposition == "QUARANTINE_BLOCK" for item in rows):
        raise DiasCutoverError("DIASI_CUTOVER_IN_FLIGHT_QUARANTINED")
    return rows


def transfer_route_and_writer(
    state: CutoverState,
    *,
    disposed_items: Iterable[InFlightItem],
    operator_phrase: str,
) -> CutoverState:
    if operator_phrase != CUTOVER_PHRASE:
        raise DiasCutoverError("DIASI_CUTOVER_OPERATOR_AUTHORITY_MISSING")
    if state.intake != "FROZEN_EXACT_SELECTED_CLASS":
        raise DiasCutoverError("DIASI_CUTOVER_TRANSFER_BEFORE_FREEZE")
    disposition_in_flight(state, disposed_items)
    return CutoverState(
        selected_class=SELECTED_CLASS,
        intake="OPEN_SUCCESSOR_EXACT_SELECTED_CLASS",
        route=SUCCESSOR_ROUTE,
        route_generation=2,
        qualification_writer=SUCCESSOR_WRITER,
        writer_generation=2,
        old_route="DISABLED_RETAINED",
        reference_assurance="COMPLETE_REFERENCE_ROUTE",
    )


def validate_live_registry(registry: Mapping[str, object]) -> CutoverState:
    if registry.get("schema") != "ovc-diasi-selected-class-live-route/v1":
        raise DiasCutoverError("DIASI_CUTOVER_REGISTRY_SCHEMA_INVALID")
    if registry.get("status") != "ACTIVE_REFERENCE_ASSURED":
        raise DiasCutoverError("DIASI_CUTOVER_REGISTRY_NOT_ACTIVE")
    if registry.get("gate_id") != CUTOVER_GATE or registry.get("operator_phrase") != CUTOVER_PHRASE:
        raise DiasCutoverError("DIASI_CUTOVER_REGISTRY_AUTHORITY_INVALID")
    state = CutoverState(
        selected_class=str(registry.get("selected_class", "")),
        intake=str(registry.get("intake", "")),
        route=str(registry.get("route", "")),
        route_generation=int(registry.get("route_generation", 0)),
        qualification_writer=str(registry.get("qualification_writer", "")),
        writer_generation=int(registry.get("writer_generation", 0)),
        old_route=str(registry.get("old_route", "")),
        reference_assurance=str(registry.get("reference_assurance", "")),
        physical_controller=str(registry.get("physical_controller", "")),
        physical_gateway=str(registry.get("physical_gateway", "")),
        parallel_physical_writer=bool(registry.get("parallel_physical_writer", True)),
    )
    expected = transfer_route_and_writer(
        freeze_selected_intake(initial_state(), packet_class=SELECTED_CLASS),
        disposed_items=(),
        operator_phrase=CUTOVER_PHRASE,
    )
    if state != expected:
        raise DiasCutoverError("DIASI_CUTOVER_REGISTRY_STATE_DRIFT")
    if registry.get("global_intake_freeze") is not False:
        raise DiasCutoverError("DIASI_CUTOVER_GLOBAL_FREEZE_DENIED")
    return state


def writer_accepts(*, writer: str, generation: int, packet_class: str) -> bool:
    if packet_class != SELECTED_CLASS:
        raise DiasCutoverError("DIASI_CUTOVER_NON_SELECTED_CLASS_NOT_OWNED")
    if generation != 2:
        raise DiasCutoverError("DIASI_CUTOVER_STALE_WRITER_FENCE")
    if writer != SUCCESSOR_WRITER:
        raise DiasCutoverError("DIASI_CUTOVER_WRITER_NOT_AUTHORISED")
    return True

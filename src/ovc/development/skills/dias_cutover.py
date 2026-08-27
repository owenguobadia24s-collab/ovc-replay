"""Fail-closed VIT owner-local route; historical module path retained."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


SELECTED_CLASS = "DSAI_VIT_RECEIPT_ONLY_V0_1"
SUCCESSOR_ROUTE = "DSAI_VIT_AND_VIT_QUALIFICATION_OWNER_LOCAL"
SUCCESSOR_WRITER = "VIT_QUALIFICATION_OWNER_LOCAL"
PHYSICAL_CONTROLLER = "DSAI_VIT_PHYSICAL_CONTROLLER"
PHYSICAL_GATEWAY = "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"
ACTIVE_GENERATION = 3


class DiasCutoverError(RuntimeError):
    """Raised when the active selected-class route or fence is unsafe."""


@dataclass(frozen=True)
class CutoverState:
    selected_class: str
    intake: str
    route: str
    route_generation: int
    qualification_writer: str
    writer_generation: int
    reference_assurance: str
    physical_controller: str = PHYSICAL_CONTROLLER
    physical_gateway: str = PHYSICAL_GATEWAY
    parallel_physical_writer: bool = False


def validate_live_registry(registry: Mapping[str, object]) -> CutoverState:
    if registry.get("schema") != "ovc-vit-owner-local-selected-class-route/v1":
        raise DiasCutoverError("VIT_OWNER_LOCAL_ROUTE_REGISTRY_SCHEMA_INVALID")
    if registry.get("status") != "ACTIVE_OWNER_LOCAL" or registry.get("owner") != "DSAI_VIT":
        raise DiasCutoverError("VIT_OWNER_LOCAL_ROUTE_NOT_ACTIVE")
    if any(key in registry for key in ("programme_id", "packet_id", "cutover_gate_id", "retirement_gate_id", "retirement_operator_phrase")):
        raise DiasCutoverError("DIASI_ACTIVE_CONTROL_BINDING_PRESENT_AFTER_SUNSET")
    if "old_route" in registry or "incumbent_writer" in registry:
        raise DiasCutoverError("DIASI_ROUTE_RETIRED_AUTHORITY_PRESENT")
    state = CutoverState(
        selected_class=str(registry.get("selected_class", "")),
        intake=str(registry.get("intake", "")),
        route=str(registry.get("route", "")),
        route_generation=int(registry.get("route_generation", 0)),
        qualification_writer=str(registry.get("qualification_writer", "")),
        writer_generation=int(registry.get("writer_generation", 0)),
        reference_assurance=str(registry.get("reference_assurance", "")),
        physical_controller=str(registry.get("physical_controller", "")),
        physical_gateway=str(registry.get("physical_gateway", "")),
        parallel_physical_writer=bool(registry.get("parallel_physical_writer", True)),
    )
    expected = CutoverState(
        selected_class=SELECTED_CLASS,
        intake="OPEN_SUCCESSOR_EXACT_SELECTED_CLASS",
        route=SUCCESSOR_ROUTE,
        route_generation=ACTIVE_GENERATION,
        qualification_writer=SUCCESSOR_WRITER,
        writer_generation=ACTIVE_GENERATION,
        reference_assurance="COMPLETE_REFERENCE_ROUTE",
    )
    if state != expected:
        raise DiasCutoverError("DIASI_ROUTE_REGISTRY_STATE_DRIFT")
    if registry.get("global_intake_freeze") is not False:
        raise DiasCutoverError("DIASI_ROUTE_GLOBAL_FREEZE_DENIED")
    return state


def writer_accepts(*, writer: str, generation: int, packet_class: str) -> bool:
    if packet_class != SELECTED_CLASS:
        raise DiasCutoverError("DIASI_ROUTE_NON_SELECTED_CLASS_NOT_OWNED")
    if generation != ACTIVE_GENERATION:
        raise DiasCutoverError("DIASI_ROUTE_STALE_WRITER_FENCE")
    if writer != SUCCESSOR_WRITER:
        raise DiasCutoverError("DIASI_ROUTE_WRITER_NOT_AUTHORISED")
    return True

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ovc.development.skills.vit_core import VitContractError

GENERAL_CONTROLLER = "DSAI_VIT_PHYSICAL_CONTROLLER"
GENERAL_GATEWAY = "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"
GENERAL_SCOPE = "NORMAL_ALREADY_AUTHORISED_AUTO_EXECUTABLE_POPULATION"


@dataclass(frozen=True)
class GeneralVitAuthority:
    authority_status: str
    controller: str
    routing_scope: str
    allowed_gate_classes: tuple[str, ...]
    required_authority_delta: str
    physical_gateway: str
    reserved_boundaries: str
    one_active_materialisation_path: bool
    one_head_at_a_time: bool
    parallel_physical_merge: bool
    grt_g3: str
    force_push: bool
    history_rewrite: bool

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> "GeneralVitAuthority":
        serialization = record.get("serialization")
        if not isinstance(serialization, Mapping):
            raise VitContractError("AUTHORITY_INVALIDATED")
        grt = record.get("grt_binding")
        return cls(
            authority_status=str(record.get("authority_status")),
            controller=str(record.get("controller")),
            routing_scope=str(record.get("routing_scope")),
            allowed_gate_classes=tuple(str(x) for x in record.get("allowed_gate_classes", ())),
            required_authority_delta=str(record.get("required_authority_delta")),
            physical_gateway=str(record.get("physical_gateway")),
            reserved_boundaries=str(record.get("reserved_boundaries")),
            one_active_materialisation_path=bool(serialization.get("one_active_materialisation_path")),
            one_head_at_a_time=bool(serialization.get("one_head_at_a_time")),
            parallel_physical_merge=bool(serialization.get("parallel_physical_merge")),
            grt_g3=str(grt.get("grt_g3")) if isinstance(grt, Mapping) else "UNKNOWN",
            force_push=bool(record.get("force_push")),
            history_rewrite=bool(record.get("history_rewrite")),
        )

    def validate(self) -> None:
        if self.authority_status != "ACTIVE":
            raise VitContractError("WAITING_OPERATOR_AUTHORITY")
        if self.controller != GENERAL_CONTROLLER or self.physical_gateway != GENERAL_GATEWAY:
            raise VitContractError("AUTHORITY_INVALIDATED")
        if self.routing_scope != GENERAL_SCOPE:
            raise VitContractError("AUTHORITY_INVALIDATED")
        if set(self.allowed_gate_classes) != {"AUTO_EXECUTABLE", "AUTO_RATIFIABLE"}:
            raise VitContractError("AUTHORITY_INVALIDATED")
        if self.required_authority_delta != "NONE":
            raise VitContractError("AUTHORITY_INVALIDATED")
        if self.reserved_boundaries != "PROGRAMME_OWNED_AND_UNCHANGED":
            raise VitContractError("AUTHORITY_INVALIDATED")
        if not self.one_active_materialisation_path or not self.one_head_at_a_time:
            raise VitContractError("INTEGRATION_EXCLUSIVITY_BREACH")
        if self.parallel_physical_merge or self.force_push or self.history_rewrite:
            raise VitContractError("INTEGRATION_EXCLUSIVITY_BREACH")
        if self.grt_g3 != "NOT_AUTHORISED":
            raise VitContractError("AUTHORITY_INVALIDATED")


@dataclass(frozen=True)
class GeneralVitPacketAdmission:
    packet_id: str
    programme_id: str
    gate_class: str
    authority_delta: str
    owner_authority_current: bool
    prerequisites_pass: bool
    qa_pass: bool
    reserved_boundary_pending: bool = False
    unresolved_warning_count: int = 0
    unresolved_review_count: int = 0


def admit_general_packet(authority: GeneralVitAuthority, packet: GeneralVitPacketAdmission) -> str:
    authority.validate()
    if packet.gate_class not in authority.allowed_gate_classes:
        return "DENY_RESERVED_GATE"
    if packet.authority_delta != "NONE":
        return "DENY_AUTHORITY_DELTA"
    if not packet.owner_authority_current:
        return "DENY_OWNER_AUTHORITY"
    if packet.reserved_boundary_pending:
        return "DENY_RESERVED_BOUNDARY"
    if not packet.prerequisites_pass:
        return "DENY_PREREQUISITE"
    if not packet.qa_pass:
        return "DENY_QA"
    if packet.unresolved_warning_count or packet.unresolved_review_count:
        return "DENY_UNRESOLVED_FINDING"
    return "ALLOW_VIT_GENERAL_SERIALIZED_GATEWAY"

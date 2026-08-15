from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import VitContractError


PILOT_PACKET_CLASS = "LOW_RISK_IMPLEMENTATION"
PILOT_CONTROLLER = "DSAI_VIT_PHYSICAL_CONTROLLER"
PILOT_GATEWAY = "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"


@dataclass(frozen=True)
class LivePilotAuthority:
    authority_status: str
    controller: str
    allowed_packet_classes: tuple[str, ...]
    packet_class_policy: str
    physical_gateway: str
    one_active_materialisation_path: bool
    one_head_at_a_time: bool
    parallel_physical_merge: bool
    grt_g3: str
    force_push: bool
    history_rewrite: bool

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> "LivePilotAuthority":
        serialization = record.get("serialization")
        if not isinstance(serialization, Mapping):
            raise VitContractError("AUTHORITY_INVALIDATED")
        return cls(
            authority_status=str(record.get("authority_status")),
            controller=str(record.get("controller")),
            allowed_packet_classes=tuple(str(x) for x in record.get("allowed_packet_classes", ())),
            packet_class_policy=str(record.get("packet_class_policy")),
            physical_gateway=str(record.get("physical_gateway")),
            one_active_materialisation_path=bool(serialization.get("one_active_materialisation_path")),
            one_head_at_a_time=bool(serialization.get("one_head_at_a_time")),
            parallel_physical_merge=bool(serialization.get("parallel_physical_merge")),
            grt_g3=str((record.get("grt_binding") or {}).get("grt_g3")) if isinstance(record.get("grt_binding"), Mapping) else "UNKNOWN",
            force_push=bool(record.get("force_push")),
            history_rewrite=bool(record.get("history_rewrite")),
        )

    def validate(self) -> None:
        if self.authority_status != "ACTIVE":
            raise VitContractError("WAITING_OPERATOR_AUTHORITY")
        if self.controller != PILOT_CONTROLLER or self.physical_gateway != PILOT_GATEWAY:
            raise VitContractError("AUTHORITY_INVALIDATED")
        if self.allowed_packet_classes != (PILOT_PACKET_CLASS,) or self.packet_class_policy != "EXACT_ALLOWLIST_ONLY":
            raise VitContractError("AUTHORITY_INVALIDATED")
        if not self.one_active_materialisation_path or not self.one_head_at_a_time:
            raise VitContractError("INTEGRATION_EXCLUSIVITY_BREACH")
        if self.parallel_physical_merge or self.force_push or self.history_rewrite:
            raise VitContractError("INTEGRATION_EXCLUSIVITY_BREACH")
        if self.grt_g3 != "NOT_AUTHORISED":
            raise VitContractError("AUTHORITY_INVALIDATED")


@dataclass(frozen=True)
class LivePilotPacketAdmission:
    packet_id: str
    packet_class: str
    gate_class: str
    authority_delta: str
    prerequisites_pass: bool
    qa_pass: bool
    unresolved_warning_count: int = 0
    unresolved_review_count: int = 0


def admit_live_pilot_packet(authority: LivePilotAuthority, packet: LivePilotPacketAdmission) -> str:
    authority.validate()
    if packet.packet_class != PILOT_PACKET_CLASS:
        return "DENY_PACKET_CLASS"
    if packet.gate_class not in {"AUTO_EXECUTABLE", "AUTO_RATIFIABLE"}:
        return "DENY_RESERVED_GATE"
    if packet.authority_delta != "NONE":
        return "DENY_AUTHORITY_DELTA"
    if not packet.prerequisites_pass:
        return "DENY_PREREQUISITE"
    if not packet.qa_pass:
        return "DENY_QA"
    if packet.unresolved_warning_count or packet.unresolved_review_count:
        return "DENY_UNRESOLVED_FINDING"
    return "ALLOW_LIVE_SERIALIZED_GATEWAY"


@dataclass(frozen=True)
class LivePilotMaterialisationReceipt:
    lane_id: str
    packet_id: str
    predecessor_commit: str
    candidate_commit: str
    predicted_tree: str
    observed_main_commit: str
    observed_tree: str
    siq_gateway: str = PILOT_GATEWAY
    parallel_merge: bool = False
    operator_intervention: bool = False
    authority_allow: bool = True

    @property
    def exact_tree_equal(self) -> bool:
        return self.predicted_tree == self.observed_tree

    @property
    def receipt_id(self) -> str:
        return canonical_sha256(asdict(self))


def evaluate_q6_receipts(receipts: Sequence[LivePilotMaterialisationReceipt]) -> dict[str, object]:
    if len(receipts) < 2:
        raise VitContractError("Q6_REQUIRES_MULTIPLE_LANES")
    false_authority_allows = sum(1 for r in receipts if not r.authority_allow)
    parallel_merges = sum(1 for r in receipts if r.parallel_merge)
    tree_mismatches = sum(1 for r in receipts if not r.exact_tree_equal)
    operator_interventions = sum(1 for r in receipts if r.operator_intervention)
    unexplained_main_divergence = 0
    for previous, current in zip(receipts, receipts[1:]):
        if current.predecessor_commit != previous.observed_main_commit:
            unexplained_main_divergence += 1
    complete_receipts = all(
        r.predecessor_commit and r.candidate_commit and r.predicted_tree and r.observed_main_commit and r.observed_tree
        for r in receipts
    )
    passed = (
        false_authority_allows == 0
        and parallel_merges == 0
        and tree_mismatches == 0
        and unexplained_main_divergence == 0
        and complete_receipts
    )
    return {
        "lane_count": len(receipts),
        "false_authority_allows": false_authority_allows,
        "parallel_merges": parallel_merges,
        "tree_mismatches": tree_mismatches,
        "unexplained_main_divergence": unexplained_main_divergence,
        "complete_end_to_end_receipts": complete_receipts,
        "operator_interventions": operator_interventions,
        "q6_pass": passed,
    }

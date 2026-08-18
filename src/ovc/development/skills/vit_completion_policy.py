from __future__ import annotations

from typing import Any, Mapping

from ovc.development.skills.vit_core import VitContractError


def _is_administrative_closeout(value: object) -> bool:
    token = str(value or "").strip().upper().replace("_", "-")
    return "CLOSEOUT" in token or "CLOSE-OUT" in token


def validate_non_churning_completion_transition(
    *, packet_id: str, completion_transition: Mapping[str, Any]
) -> None:
    """Prevent post-merge administrative closeout from becoming another PR.

    A permanent VIT packet may finish as COMPLETED, GATE_READY, BLOCKED or
    another owner-defined state, and may name the next *substantive* packet.
    It may not model an administrative post-merge closeout as either the packet
    being integrated or its next packet.  Post-write physical facts belong in
    PhysicalMaterialisationReceipt / PacketCompletionReceipt and the existing
    content-addressed completion bundle.

    This is intentionally a construction-time rule.  Historical lineage remains
    valid and recoverable; no already-frozen PIP identity is rewritten.
    """

    if _is_administrative_closeout(packet_id):
        raise VitContractError(
            "VIT_ADMINISTRATIVE_CLOSEOUT_PR_PROHIBITED_USE_RECEIPT_PATH"
        )
    next_packet = completion_transition.get("next_packet")
    if next_packet is not None and _is_administrative_closeout(next_packet):
        raise VitContractError(
            "VIT_ADMINISTRATIVE_CLOSEOUT_PR_PROHIBITED_USE_RECEIPT_PATH"
        )

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import pilot_corr2_review_closure as corr2


TERMINAL_CORR2_STATUS = "COMPLETED_IN_MAIN_AND_SIGNED_OPERATOR_REREVIEW_COMPLETE"
_ORIGINAL_LOAD_CORR2_AUTHORITY = corr2.load_corr2_authority


def load_corr2_authority_with_terminal_review(
    repository_root: Path,
) -> dict[str, Any]:
    """Accept the exact post-CORR2 terminal state required by CORR3.

    CORR2's original loader predates the signed local re-review court-record
    transition. CORR3 must accept that one exact terminal status while retaining
    every existing operator-decision, packet, replay-boundary and gate-bundle
    check. No other status is broadened or normalized.
    """

    try:
        return _ORIGINAL_LOAD_CORR2_AUTHORITY(repository_root)
    except corr2.Corr2ReviewError as exc:
        expected = f"CORR2_STATE_NOT_EXECUTABLE:{TERMINAL_CORR2_STATUS}"
        if str(exc) != expected:
            raise

    decision = corr2._repo_json(
        repository_root,
        "docs/releases/opt-b-c1-v2/corrective/c1c-g5/operator-gate/"
        "C1C_G5_CORRECTIVE_PILOT_REVIEW_OPERATOR_DECISION.json",
        "CORR2_OPERATOR_DECISION_UNAVAILABLE",
    )
    state = corr2._repo_json(
        repository_root,
        "registries/research_operations/pattern_discovery/"
        "PD_C1C_G5_PILOT_CORRECTIVE_STATE_v0_1.json",
        "CORR2_PROGRAMME_STATE_UNAVAILABLE",
    )
    bundle = corr2._repo_json(
        repository_root,
        "docs/releases/opt-b-c1-v2/corrective/c1c-g5/operator-gate/"
        "C1C_G5_CORRECTIVE_PILOT_REVIEW_GATE_READY_BUNDLE.json",
        "CORR2_GATE_READY_BUNDLE_UNAVAILABLE",
    )

    if decision.get("gate_id") != corr2.RETURN_GATE or decision.get("decision") != "DEFER":
        raise corr2.Corr2ReviewError("CORR2_OPERATOR_DEFER_NOT_RECORDED")
    packet = decision.get("authorised_next_packet")
    if not isinstance(packet, Mapping) or packet.get("packet_id") != corr2.PACKET_ID:
        raise corr2.Corr2ReviewError("CORR2_PACKET_AUTHORITY_NOT_RECORDED")
    if packet.get("machine_replay") != "DENIED_NOT_REQUIRED":
        raise corr2.Corr2ReviewError("CORR2_MACHINE_REPLAY_BOUNDARY_INVALID")

    corr2_state = state.get("corr2")
    if not isinstance(corr2_state, Mapping) or corr2_state.get("packet_id") != corr2.PACKET_ID:
        raise corr2.Corr2ReviewError("CORR2_STATE_PACKET_MISMATCH")
    if corr2_state.get("status") != TERMINAL_CORR2_STATUS:
        raise corr2.Corr2ReviewError(
            f"CORR2_STATE_NOT_EXECUTABLE:{corr2_state.get('status')}"
        )

    recommended = bundle.get("recommended_decision")
    if (
        bundle.get("gate_id") != corr2.RETURN_GATE
        or not isinstance(recommended, Mapping)
        or recommended.get("decision") != "DEFER"
    ):
        raise corr2.Corr2ReviewError("CORR2_GATE_READY_SOURCE_MISMATCH")

    return {"decision": decision, "state": state, "bundle": bundle}


# Install only for the CORR3 command entrypoint. Direct CORR2 execution keeps the
# original loader and historical state contract.
corr2.load_corr2_authority = load_corr2_authority_with_terminal_review

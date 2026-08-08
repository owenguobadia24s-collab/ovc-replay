from __future__ import annotations

from typing import Any, Mapping

from .builder import OccurrenceContextError
from .models import ContextDependencyRef, OccurrenceAnchorRef
from .serialization import logical_hash

ALLOWED_CLOCKS = {"15M", "2H_A_L"}


def c2_anchor_from_state(state: Mapping[str, Any]) -> OccurrenceAnchorRef:
    required = ("c2_state_id", "first_valid_time", "clock", "side", "evaluation_scope_id")
    missing = [field for field in required if not state.get(field)]
    if missing:
        raise OccurrenceContextError("OC_AVAIL_ANCHOR_MISSING", ",".join(missing))
    scope = str(state["evaluation_scope_id"])
    if not scope.startswith("GBPUSD-"):
        raise OccurrenceContextError("OC_AUTH_NEW_INSTRUMENT_DENIED")
    if state["side"] not in {"BID", "ASK"}:
        raise OccurrenceContextError("OC_AUTH_NEW_SIDE_DENIED")
    if state["clock"] not in ALLOWED_CLOCKS:
        raise OccurrenceContextError("OC_AUTH_NEW_CLOCK_DENIED")
    return OccurrenceAnchorRef(
        anchor_kind="C2_OBSERVATION",
        anchor_id=str(state["c2_state_id"]),
        anchor_schema_id="c2_parallel_state/v0_1",
        anchor_logical_hash=logical_hash(dict(state)),
        anchor_first_valid_time=str(state["first_valid_time"]),
        source_release_id=str(state.get("opt_a_release_id") or state.get("c1_release_id") or ""),
    )


def c2_source_context(state: Mapping[str, Any]) -> dict[str, Any]:
    anchor = c2_anchor_from_state(state)
    return {
        "instrument_id": "GBPUSD",
        "price_side": str(state["side"]),
        "source_release_id": anchor.source_release_id,
        "manifest_id": str(state.get("opt_a_manifest_id") or state.get("c1_manifest_id") or ""),
        "source_manifest_hash": None,
    }


def c2_dependency(state: Mapping[str, Any]) -> ContextDependencyRef:
    anchor = c2_anchor_from_state(state)
    return ContextDependencyRef(
        dependency_kind="C2_STATE",
        record_id=anchor.anchor_id,
        schema_id=anchor.anchor_schema_id,
        logical_hash=anchor.anchor_logical_hash,
        first_valid_time=anchor.anchor_first_valid_time,
        dependency_role="ANCHOR",
        required=True,
        source_release_id=anchor.source_release_id,
    )

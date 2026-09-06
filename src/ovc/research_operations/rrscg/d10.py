"""Inactive RRSCG-D10 reducer pack.

D10 supersedes D9 only at the selected-Q reducer interface.  It consumes an
already-verified D9 observer-state record and cannot construct or mutate D9
state, geometry, motion, trajectory, owner truth, or source authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .d9 import D9StateRecord
from .d10_reference_core import (
    _D9_CONTROL_HIERARCHY,
    _D10_SUCCESSOR_HIERARCHY,
    _select_reducer,
)
from .kernel import PRIMARY_CONSTRAINT_VIEWS

D10_ALGORITHM_ID = "OVC-EML-GRAMMAR-0003-RRSCG-DYNAMICS-ALGORITHM-0.2-D10"
D10_PACKAGE_SHA256 = "6b58e9edbb16dd5f8e6f182d0af82c46279a28fc030b4d560bcd69635729515f"
D10_RELEASE_BUNDLE_SHA256 = "092bf144b38f84a43946d36a15d0905c2bce7f51e7ca815e6814eae361d1ad67"
D10_RELEASE_BINDING_SHA256 = "cb2315d01379138c1f62d6b1cacc89d9b1314bf2532602e264b7d223a27bf099"
D10_REDUCER_PACK_ID = "RRSCG_D10_C_LAST_REDUCER_v1"
D10_CLAIM_CAP = "DESCRIPTIVE_DEVELOPMENT_ONLY"
D10_CAPABILITY_STATE = "INACTIVE"


class D10ReducerBindingError(ValueError):
    """Raised when the supplied D9 state is not an exact lawful reducer parent."""


@dataclass(frozen=True)
class D10ReducerRecord:
    event_id: str
    source_generation_id: str
    stream_segment_id: str
    reducer_pack_id: str
    parent_d9_state_sha256: str
    selected_frontier: tuple[str, ...]
    selected_resolution_tier: str
    relation_resolved: bool


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def reduce_d9_state(state: D9StateRecord) -> D10ReducerRecord:
    """Apply the exact D10 successor hierarchy to one verified D9 state.

    The immutable D9/R2 control result is recomputed and reconciled before the
    D10 tier is considered.  Any change outside the one frozen
    ``MINIMAL_CONSTRAINT -> C_LAST_FAMILY_CONSENSUS`` edge fails closed.
    """
    payload = state.state_shape_payload
    views = payload.get("view_evidence_records")
    if not isinstance(views, list):
        raise D10ReducerBindingError("D10_REQUIRES_D9_VIEW_EVIDENCE_RECORDS")
    if {str(row.get("view_id")) for row in views} != set(PRIMARY_CONSTRAINT_VIEWS):
        raise D10ReducerBindingError("D10_D9_VIEWSET_MISMATCH")

    d9_q, d9_tier = _select_reducer(views, _D9_CONTROL_HIERARCHY)
    parent_q = sorted(payload.get("Q", {}).get("target_ids", []))
    parent_tier = payload.get("resolution_tier") or "NONE"
    parent_resolved = payload.get("q_state") == "RESOLVED_NONEMPTY"
    if d9_q != parent_q or d9_tier != parent_tier or bool(d9_q) != parent_resolved:
        raise D10ReducerBindingError("IMMUTABLE_PARENT_R2_CONTROL_MISMATCH")

    d10_q, d10_tier = _select_reducer(views, _D10_SUCCESSOR_HIERARCHY)
    if d10_tier != d9_tier:
        if not (
            d9_tier == "MINIMAL_CONSTRAINT"
            and d10_tier == "C_LAST_FAMILY_CONSENSUS"
            and set(d10_q).issubset(set(d9_q))
        ):
            raise D10ReducerBindingError("D10_REDUCER_DELTA_OUTSIDE_FROZEN_CANDIDATE")
    elif d10_q != d9_q:
        raise D10ReducerBindingError("D10_NONCANDIDATE_Q_CHANGE")

    envelope = set(payload.get("E", {}).get("target_ids", []))
    if not set(d10_q).issubset(envelope):
        raise D10ReducerBindingError("D10_Q_OUTSIDE_D9_ENVELOPE")

    return D10ReducerRecord(
        event_id=state.event_id,
        source_generation_id=state.source_generation_id,
        stream_segment_id=state.stream_segment_id,
        reducer_pack_id=D10_REDUCER_PACK_ID,
        parent_d9_state_sha256=_canonical_sha256(payload),
        selected_frontier=tuple(d10_q),
        selected_resolution_tier=d10_tier,
        relation_resolved=bool(d10_q),
    )

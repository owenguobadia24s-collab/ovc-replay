"""Inactive repository-native RRSCG-D9 observer-state transport.

This module binds the exact D9 state/geometry/kinematics mechanics to the
repository-native immutable R2 continuation-constraint kernel. It does not
activate RRSCG, create a regime/latent-state ontology, change C2/C2E owner
truth, or grant scientific/predictive/exposure authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .kernel import ConstraintGrammarEvent, PRIMARY_CONSTRAINT_VIEWS
from .d9_reference_core import _build_motion, _build_state, _derive_view

D9_ALGORITHM_ID = "OVC-EML-GRAMMAR-0003-RRSCG-DYNAMICS-ALGORITHM-0.2-D9"
D9_IMPLEMENTATION_SOURCE_SHA256 = "15c4f3c5bca53e40894c54c8d4cffdca2675a8f62a537efe1b2533efb09bb23a"
D9_PACKAGE_SHA256 = "edbb3e0448845eee375dbefdf2f33fe2d6df3c1ffd4605b28dc117576d7ea398"
D9_CLAIM_CAP = "DESCRIPTIVE_DEVELOPMENT_ONLY"
D9_CAPABILITY_STATE = "INACTIVE"


class D9BindingError(ValueError):
    pass


@dataclass(frozen=True)
class D9StateRecord:
    event_id: str
    source_generation_id: str
    stream_segment_id: str
    state_shape_payload: dict[str, Any]


@dataclass(frozen=True)
class D9MotionRecord:
    predecessor_event_id: str
    current_event_id: str
    stream_segment_id: str
    motion_shape_payload: dict[str, Any]


def _parent_payload(event: ConstraintGrammarEvent) -> dict[str, Any]:
    return {
        "selected_frontier_target_ids": sorted(event.selected_frontier),
        "relation_resolved": bool(event.relation_resolved),
        "selected_resolution_tier": event.selected_resolution_tier,
        "full_consensus_state": event.full_consensus_state,
    }


def _validate_raw_views_against_r2(
    event: ConstraintGrammarEvent,
    raw_view_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if event.representation_set_id != "RRSCG_OPERATION_FREE_VIEWSET_v1":
        raise D9BindingError("D9_REQUIRES_FROZEN_R2_OPERATION_FREE_VIEWSET")
    by_raw = {str(row["view_id"]): dict(row) for row in raw_view_records}
    if set(by_raw) != set(PRIMARY_CONSTRAINT_VIEWS):
        raise D9BindingError("D9_RAW_VIEWSET_MISMATCH")
    by_event = {view.view_id: view for view in event.views}
    if set(by_event) != set(PRIMARY_CONSTRAINT_VIEWS):
        raise D9BindingError("D9_R2_EVENT_VIEWSET_MISMATCH")

    ordered: list[dict[str, Any]] = []
    for view_id in PRIMARY_CONSTRAINT_VIEWS:
        raw = by_raw[view_id]
        derived = _derive_view(raw, int(event.support_min), int(event.relation_min))
        parent = by_event[view_id]
        if int(raw["antecedent_support_count"]) != int(parent.antecedent_support):
            raise D9BindingError(f"D9_R2_SUPPORT_COUNT_MISMATCH:{view_id}")
        if bool(derived["antecedent_supported"]) != bool(parent.supported):
            raise D9BindingError(f"D9_R2_ANTECEDENT_SUPPORT_MISMATCH:{view_id}")
        if set(derived["qualified_frontier_target_ids"]) != set(parent.qualified_frontier):
            raise D9BindingError(f"D9_R2_QUALIFIED_FRONTIER_MISMATCH:{view_id}")
        expected_rel = sorted(
            (
                {"target_id": target_id, "support_count": int(n)}
                for target_id, n in parent.observed_frontier_supports
            ),
            key=lambda x: x["target_id"],
        )
        actual_rel = sorted(
            (
                {"target_id": str(x["target_id"]), "support_count": int(x["support_count"])}
                for x in raw["relation_support_records"]
            ),
            key=lambda x: x["target_id"],
        )
        if expected_rel != actual_rel:
            raise D9BindingError(f"D9_R2_RELATION_SUPPORT_MISMATCH:{view_id}")
        ordered.append(raw)
    return ordered


def build_observer_state(
    event: ConstraintGrammarEvent,
    raw_view_records: Sequence[Mapping[str, Any]],
    *,
    stream_segment_id: str,
    namespace_id: str = "RRSCG_D9_REPOSITORY_NATIVE_v1",
) -> D9StateRecord:
    """Build one exact D9 ConstraintState from a repository R2 event.

    `raw_view_records` preserve source-evaluable/comparability distinctions that
    the static R2 event intentionally does not own. They are verified against
    the exact repository R2 output before D9 state construction.
    """
    raw = _validate_raw_views_against_r2(event, raw_view_records)
    payload = _build_state(
        namespace_id,
        raw,
        int(event.support_min),
        int(event.relation_min),
        _parent_payload(event),
    )
    return D9StateRecord(
        event_id=event.event_id,
        source_generation_id=event.source_generation_id,
        stream_segment_id=str(stream_segment_id),
        state_shape_payload=payload,
    )


def build_observer_motion(
    previous: D9StateRecord,
    current: D9StateRecord,
    *,
    namespace_id: str = "RRSCG_D9_REPOSITORY_NATIVE_v1",
) -> D9MotionRecord:
    if previous.source_generation_id != current.source_generation_id:
        raise D9BindingError("D9_CROSS_GENERATION_MOTION_FORBIDDEN")
    if previous.stream_segment_id != current.stream_segment_id:
        raise D9BindingError("D9_CROSS_SEGMENT_MOTION_FORBIDDEN")
    payload = _build_motion(
        namespace_id,
        previous.state_shape_payload,
        current.state_shape_payload,
    )
    return D9MotionRecord(
        predecessor_event_id=previous.event_id,
        current_event_id=current.event_id,
        stream_segment_id=current.stream_segment_id,
        motion_shape_payload=payload,
    )


def build_observer_trajectory(
    records: Sequence[tuple[ConstraintGrammarEvent, Sequence[Mapping[str, Any]], str]],
    *,
    namespace_id: str = "RRSCG_D9_REPOSITORY_NATIVE_v1",
) -> tuple[tuple[D9StateRecord, ...], tuple[D9MotionRecord, ...]]:
    states = tuple(
        build_observer_state(event, raw_views, stream_segment_id=segment, namespace_id=namespace_id)
        for event, raw_views, segment in records
    )
    motions: list[D9MotionRecord] = []
    for previous, current in zip(states, states[1:]):
        if (
            previous.source_generation_id == current.source_generation_id
            and previous.stream_segment_id == current.stream_segment_id
        ):
            motions.append(build_observer_motion(previous, current, namespace_id=namespace_id))
    return states, tuple(motions)

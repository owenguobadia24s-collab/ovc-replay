from __future__ import annotations

from typing import Any, Mapping

PANEL_ORDER = (
    "C2_STATE",
    "C2_TRANSITION",
    "PERSISTENCE_CONFLICT",
    "RO4_SEQUENCE",
    "BOUNDARY_FRICTION_READ_ONLY",
    "PD_TRIGGER_TRACE_ONLY",
    "SIGNATURE_DIVERSITY",
    "SAMPLE_DISCLOSURE",
)

PANEL_TITLES = {
    "C2_STATE": "C2 state evidence",
    "C2_TRANSITION": "C2 transition evidence",
    "PERSISTENCE_CONFLICT": "Persistence and conflict evidence",
    "RO4_SEQUENCE": "Non-canonical sequence evidence",
    "BOUNDARY_FRICTION_READ_ONLY": "Boundary and friction records",
    "PD_TRIGGER_TRACE_ONLY": "Pattern Discovery trigger traces",
    "SIGNATURE_DIVERSITY": "Signature diversity audit",
    "SAMPLE_DISCLOSURE": "Sample disclosure",
}


def build_c2_sequence_evidence_view(projection: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(projection or {})
    availability = str(source.get("availability", "NOT_EVALUATED"))
    base = {
        "schema": "ovc-research-console-rc-g5-c2-sequence-view/v1",
        "route_id": source.get("route_id", "RESEARCH.C2_SEQUENCE_EVIDENCE"),
        "route_state": source.get("route_state", "ENABLED_LOCAL_READ_ONLY"),
        "route_enabled": bool(source.get("route_enabled", True)),
        "availability": availability,
        "authority": "LOCAL_READ_ONLY_C2_SEQUENCE_EVIDENCE_PRESENTATION",
        "authority_banners": list(source.get("authority_banners") or []),
        "validation_consumption": "LOCKED_UNCONSUMED",
        "c2_authority": "UNCHANGED",
        "pattern_discovery_authority": "UNCHANGED",
        "read_only": True,
        "writes": "NONE",
        "annotation_actions": "NONE",
        "remote_deployment": "DENIED",
        "operator_decision_id": source.get("operator_decision_id"),
    }
    grouped: dict[str, list[dict[str, Any]]] = {panel_class: [] for panel_class in PANEL_ORDER}
    if availability != "AVAILABLE":
        return {
            **base,
            "status": str(source.get("reason", "RO4_PROJECTION_NOT_EVALUATED")),
            "source_commit": "NOT_EVALUATED",
            "source_projection_id": "NOT_EVALUATED",
            "source_logical_hash": "NOT_EVALUATED",
            "source_release_refs": [],
            "panel_order": list(PANEL_ORDER),
            "panels": grouped,
        }

    for panel in source.get("panels", []):
        if not isinstance(panel, Mapping):
            continue
        panel_class = str(panel.get("panel_class", ""))
        if panel_class not in grouped:
            continue
        grouped[panel_class].append(
            {
                "panel_id": panel.get("panel_id"),
                "panel_class": panel_class,
                "payload": dict(panel.get("payload") or {}),
            }
        )

    return {
        **base,
        "status": "READY",
        "source_commit": source.get("source_commit"),
        "source_projection_id": source.get("source_projection_id"),
        "source_logical_hash": source.get("source_logical_hash"),
        "source_release_refs": [dict(item) for item in source.get("source_release_refs", []) if isinstance(item, Mapping)],
        "panel_order": list(PANEL_ORDER),
        "panels": grouped,
    }


def render_c2_sequence_evidence(projection: Mapping[str, Any] | None) -> None:
    """Render the RC-G5 local read-only route without controls or write paths."""

    import streamlit as st

    view = build_c2_sequence_evidence_view(projection)
    st.markdown('<div class="ovc-panel-title">C2 Sequence Evidence · local read only</div>', unsafe_allow_html=True)
    st.caption(
        f"Route {view['route_state']} · authority {view['authority']} · "
        "Validation LOCKED_UNCONSUMED · no annotation or write actions"
    )
    for banner in view["authority_banners"]:
        st.warning(str(banner))

    if view["availability"] != "AVAILABLE":
        st.info(
            "The RC-G5 route is active, but no admissible current RO4 projection is available. "
            f"State: {view['status']}. No market, sequence or Pattern Discovery claim is inferred."
        )
        return

    st.markdown(
        "**Source projection:** "
        f"{view.get('source_projection_id')} · commit {view.get('source_commit')}"
    )
    st.caption(f"Logical hash {view.get('source_logical_hash')}")
    with st.expander("Exact source release bindings", expanded=False):
        st.json(view["source_release_refs"])

    for panel_class in view["panel_order"]:
        rows = view["panels"][panel_class]
        with st.container(border=True):
            st.markdown(f"#### {PANEL_TITLES[panel_class]}")
            st.caption(panel_class)
            if not rows:
                st.info("NOT_EVALUATED · no admissible panel object is present for this class.")
                continue
            for row in rows:
                st.caption(str(row.get("panel_id")))
                st.json(row.get("payload") or {})

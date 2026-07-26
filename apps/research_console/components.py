from __future__ import annotations

from html import escape
from typing import Any, Iterable, Mapping

KNOWN_STATUSES = {
    "PASS", "WARN", "BLOCK", "QUARANTINE", "NOT_EVALUATED", "NOT_MATERIALIZED",
    "INCOMPLETE", "STALE", "NOT_APPLICABLE", "UNRESOLVED", "CENSORED", "MISSING", "EXPECTED_EMPTY",
}
STATUS_COLOURS = {
    "PASS": "#25C281", "WARN": "#F3B94E", "BLOCK": "#EF5A67", "MISSING": "#EF5A67",
    "QUARANTINE": "#8B5CF6", "NOT_EVALUATED": "#8B5CF6", "NOT_MATERIALIZED": "#8B5CF6",
    "INCOMPLETE": "#8B5CF6", "STALE": "#8B5CF6", "CENSORED": "#8B5CF6",
    "NOT_APPLICABLE": "#64748B", "UNRESOLVED": "#8B5CF6", "EXPECTED_EMPTY": "#64748B",
}


def _streamlit():
    import streamlit as st
    return st


def normalize_status(status: str) -> str:
    candidate = str(status).upper().strip()
    return candidate if candidate in KNOWN_STATUSES else "BLOCK"


def status_html(status: str, label: str | None = None) -> str:
    normalized = normalize_status(status)
    shown = label or normalized.replace("_", " ")
    return f'<span class="ovc-status ovc-status-{normalized.lower()}">{escape(shown)}</span>'


def render_metric_card(label: str, value: str, note: str = "") -> None:
    st = _streamlit()
    st.markdown(
        '<div class="ovc-card">'
        f'<div class="ovc-card-title">{escape(str(label))}</div>'
        f'<div class="ovc-card-value">{escape(str(value))}</div>'
        f'<div class="ovc-card-note">{escape(str(note))}</div>'
        '</div>', unsafe_allow_html=True,
    )


def render_empty_state(status: str, reason: str, consequence: str, next_action: str) -> None:
    st = _streamlit()
    normalized = normalize_status(status)
    st.markdown(
        '<div class="ovc-empty-state">'
        f'<strong>{escape(normalized.replace("_", " "))}</strong>'
        f'<p><b>Reason:</b> {escape(reason)}</p>'
        f'<p><b>Consequence:</b> {escape(consequence)}</p>'
        f'<p><b>Next valid action:</b> {escape(next_action)}</p>'
        '</div>', unsafe_allow_html=True,
    )


def render_health_card(item: Mapping[str, Any], *, button_key: str) -> bool:
    st = _streamlit()
    status = normalize_status(str(item.get("status", "BLOCK")))
    progress = max(0.0, min(1.0, float(item.get("progress", 0.0))))
    colour = STATUS_COLOURS[status]
    st.markdown(
        '<div class="ovc-health-card">'
        f'<div class="ovc-health-label">{escape(str(item.get("label", "Unknown domain")))}</div>'
        f'{status_html(status)}'
        f'<div class="ovc-health-detail">{escape(str(item.get("detail", "No detail.")))}</div>'
        f'<div class="ovc-progress"><span style="width:{progress * 100:.0f}%;background:{colour}"></span></div>'
        '</div>', unsafe_allow_html=True,
    )
    return st.button("Inspect", key=button_key, use_container_width=True)


def render_evidence_card(item: Mapping[str, Any], *, button_key: str) -> bool:
    st = _streamlit()
    role = str(item.get("label", "Evidence")).split()[0].upper()
    role_class = role.lower() if role in {"SUPPORT", "CONTRADICTION", "BOUNDARY", "NULL"} else "null"
    st.markdown(
        '<div class="ovc-evidence-card">'
        f'<span class="ovc-evidence-role ovc-evidence-{role_class}">{escape(role)}</span>'
        f'<div class="ovc-panel-title">{escape(str(item.get("label", "Evidence")))}</div>'
        f'<div class="ovc-panel-note">{escape(str(item.get("summary", "")))}</div>'
        f'{status_html(str(item.get("status", "BLOCK")))}'
        '</div>', unsafe_allow_html=True,
    )
    return st.button("Open evidence", key=button_key, use_container_width=True)


def render_source_refs(source_refs: Iterable[str]) -> None:
    st = _streamlit()
    refs = tuple(str(ref) for ref in source_refs)
    if not refs:
        render_empty_state("MISSING", "No immutable source reference is attached.", "SOURCE_RESOLUTION_BLOCKED", "Restore the source reference before using this object.")
        return
    for ref in refs:
        st.markdown(f'<div class="ovc-source-ref">{escape(ref)}</div>', unsafe_allow_html=True)


def render_drawer(item: Mapping[str, Any] | None) -> None:
    st = _streamlit()
    st.markdown('<div class="ovc-kicker">Contextual detail</div>', unsafe_allow_html=True)
    if item is None:
        render_empty_state("NOT_MATERIALIZED", "No object is selected.", "Drawer remains inactive.", "Select a health cell, evidence card, release, gate or activity event.")
        return
    st.markdown(f'<div class="ovc-panel-title">{escape(str(item.get("label", item.get("object_id", "Selected object"))))}</div>', unsafe_allow_html=True)
    st.markdown(status_html(str(item.get("status", "BLOCK"))), unsafe_allow_html=True)
    st.write(str(item.get("summary", item.get("detail", "No summary."))))
    st.caption(f"Object ID: {item.get('object_id', 'UNRESOLVED')}")
    st.write(f"**Authority:** `{item.get('authority', 'UNRESOLVED')}`")
    st.write(f"**Consequence:** {item.get('consequence', 'NOT_EVALUATED')}")
    st.write(f"**Next valid action:** {item.get('next_action', 'Inspect the governing source.')}")
    with st.expander("Lineage and source references", expanded=True):
        lineage = item.get("lineage", [])
        if lineage:
            st.write(" → ".join(str(value) for value in lineage))
        render_source_refs(item.get("source_refs", []))
    with st.expander("Raw fixture payload", expanded=False):
        st.json(dict(item))


def render_activity_rows(activity: Iterable[Mapping[str, Any]], *, on_select) -> None:
    st = _streamlit()
    rows = tuple(activity)
    if not rows:
        render_empty_state("NOT_EVALUATED", "No source-derived fixture events are present.", "No activity claim is made.", "Select another fixture condition or wait for a later live-projection gate.")
        return
    for index, event in enumerate(rows):
        cols = st.columns([0.7, 1.1, 1.0, 4.2, 1.0])
        cols[0].caption(str(event.get("time", "—")))
        cols[1].write(f"**{event.get('type', 'EVENT')}**")
        cols[2].markdown(status_html(str(event.get("status", "BLOCK"))), unsafe_allow_html=True)
        cols[3].write(str(event.get("description", "")))
        if cols[4].button("Open", key=f"activity::{index}::{event.get('object_id')}"):
            on_select(str(event.get("object_id")))

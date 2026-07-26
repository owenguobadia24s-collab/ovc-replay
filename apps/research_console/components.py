from __future__ import annotations

from html import escape
from typing import Any, Iterable, Mapping


KNOWN_STATUSES = {
    "PASS",
    "WARN",
    "BLOCK",
    "QUARANTINE",
    "NOT_EVALUATED",
    "INCOMPLETE",
    "STALE",
    "NOT_APPLICABLE",
    "UNRESOLVED",
    "CENSORED",
    "MISSING",
}


def _streamlit():
    import streamlit as st

    return st


def normalize_status(status: str) -> str:
    candidate = str(status).upper().strip()
    return candidate if candidate in KNOWN_STATUSES else "BLOCK"


def render_status_badge(status: str, *, label: str | None = None) -> None:
    st = _streamlit()
    normalized = normalize_status(status)
    shown = label or normalized.replace("_", " ")
    css_class = normalized.lower()
    st.markdown(
        f'<span class="ovc-status ovc-status-{css_class}" aria-label="Status: {escape(shown)}">{escape(shown)}</span>',
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, note: str = "") -> None:
    st = _streamlit()
    st.markdown(
        "<div class=\"ovc-card\">"
        f"<div class=\"ovc-card-title\">{escape(str(label))}</div>"
        f"<div class=\"ovc-card-value\">{escape(str(value))}</div>"
        f"<div class=\"ovc-card-note\">{escape(str(note))}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_empty_state(state: Mapping[str, Any]) -> None:
    st = _streamlit()
    status = normalize_status(str(state.get("status", "BLOCK")))
    reason = str(state.get("reason", "The surface cannot be rendered safely."))
    consequence = str(state.get("consequence", "NO_PROGRESSION"))
    next_action = str(state.get("next_action", "Inspect the governing source or gate packet."))
    st.markdown(
        "<div class=\"ovc-empty-state\">"
        f"<strong>{escape(status.replace('_', ' '))}</strong>"
        f"<p><b>Reason:</b> {escape(reason)}</p>"
        f"<p><b>Consequence:</b> {escape(consequence)}</p>"
        f"<p><b>Next valid action:</b> {escape(next_action)}</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_source_refs(source_refs: Iterable[str]) -> None:
    st = _streamlit()
    refs = tuple(str(ref) for ref in source_refs)
    if not refs:
        render_empty_state(
            {
                "status": "MISSING",
                "reason": "No immutable source references are attached.",
                "consequence": "SOURCE_RESOLUTION_BLOCKED",
                "next_action": "Restore the source reference before using this view.",
            }
        )
        return
    st.markdown('<div class="ovc-section-title">Source references</div>', unsafe_allow_html=True)
    for ref in refs:
        st.markdown(f'<div class="ovc-source-card">{escape(ref)}</div>', unsafe_allow_html=True)


def render_fixture_surface(fixture: Mapping[str, Any]) -> None:
    st = _streamlit()
    status = normalize_status(str(fixture.get("status", "BLOCK")))
    st.markdown(
        f'<div class="ovc-route-kicker">{escape(str(fixture.get("group", "UNKNOWN")))}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="ovc-section-title">{escape(str(fixture.get("label", "Unknown route")))}</div>',
        unsafe_allow_html=True,
    )
    render_status_badge(status)
    st.markdown(
        f'<div class="ovc-fixture-notice">{escape(str(fixture.get("summary", "")))}</div>',
        unsafe_allow_html=True,
    )

    metrics = list(fixture.get("metrics", []))
    if metrics:
        columns = st.columns(min(3, len(metrics)))
        for index, metric in enumerate(metrics):
            with columns[index % len(columns)]:
                render_metric_card(
                    str(metric.get("label", "Metric")),
                    str(metric.get("value", "—")),
                    str(metric.get("note", "")),
                )

    rows = list(fixture.get("rows", []))
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    elif "empty_state" in fixture:
        render_empty_state(fixture["empty_state"])

    with st.expander("Authority and fixture provenance", expanded=False):
        st.write(f"Route authority: `{fixture.get('authority', 'UNKNOWN')}`")
        st.write(f"Fixture mode: `{fixture.get('fixture_mode', 'UNKNOWN')}`")
        render_source_refs(fixture.get("source_refs", []))

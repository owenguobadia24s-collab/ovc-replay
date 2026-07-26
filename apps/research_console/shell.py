from __future__ import annotations

from html import escape
from typing import Any, Mapping

from apps.research_console.components import render_fixture_surface, render_status_badge
from apps.research_console.fixtures import FIXTURE_MODES, fixture_for_route
from apps.research_console.navigation import DEFAULT_ROUTE_ID, get_route, grouped_routes
from apps.research_console.theme import load_css_text


AUTHORITY_BOUNDARY: dict[str, str] = {
    "mode": "READ_ONLY",
    "repository_mutation": "NONE",
    "selector_mutation": "NONE",
    "threshold_mutation": "NONE",
    "market_classification": "NONE",
    "probability": "NONE",
    "exposure": "NONE",
    "execution": "NONE",
    "agent": "NONE",
    "deployment": "LOCAL_ONLY",
}


def _streamlit():
    import streamlit as st

    return st


def configure_page() -> None:
    st = _streamlit()
    st.set_page_config(
        page_title="OVC Research Console",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={"Get help": None, "Report a bug": None, "About": "OVC Research Console v0.2 · local read-only operator surface"},
    )
    st.markdown(f"<style>{load_css_text()}</style>", unsafe_allow_html=True)


def render_navigation() -> tuple[str, str]:
    st = _streamlit()
    st.session_state.setdefault("active_route_id", DEFAULT_ROUTE_ID)
    st.session_state.setdefault("fixture_mode", "VALID")

    with st.sidebar:
        st.markdown('<div class="ovc-brand">OVC</div>', unsafe_allow_html=True)
        st.markdown('<div class="ovc-subtitle">Research Console v0.2</div>', unsafe_allow_html=True)
        st.markdown('<span class="ovc-local-badge">LOCAL · READ ONLY</span>', unsafe_allow_html=True)
        st.divider()

        for group, routes in grouped_routes():
            st.caption(group.title())
            for route in routes:
                active = route.route_id == st.session_state.active_route_id
                button_label = f"{route.icon}  {route.label}" + ("  •" if active else "")
                if st.button(button_label, key=f"route::{route.route_id}", use_container_width=True):
                    st.session_state.active_route_id = route.route_id
                    st.rerun()

        st.divider()
        st.caption("RC-WP1 fixture state")
        st.session_state.fixture_mode = st.selectbox(
            "Presentation condition",
            FIXTURE_MODES,
            index=FIXTURE_MODES.index(st.session_state.fixture_mode),
            help="Fixture-only shell verification. This does not activate live v0.2 projections.",
        )

    get_route(st.session_state.active_route_id)
    return st.session_state.active_route_id, st.session_state.fixture_mode


def render_context_bar(context: Mapping[str, Any]) -> None:
    st = _streamlit()
    source_commit = escape(str(context.get("source_commit", "NOT_EVALUATED")))
    model_sha = escape(str(context.get("read_model_sha256", "NOT_EVALUATED")))
    built_at = escape(str(context.get("built_at_utc", "NOT_EVALUATED")))
    model_status = escape(str(context.get("model_status", "NOT_EVALUATED")))
    st.markdown(
        "<div class=\"ovc-context-bar\">"
        "<span class=\"ovc-local-badge\">LOCAL</span>"
        f"<span class=\"ovc-chip\">source {source_commit}</span>"
        f"<span class=\"ovc-chip\">model {model_sha}</span>"
        f"<span class=\"ovc-chip\">built {built_at}</span>"
        f"<span class=\"ovc-chip\">state {model_status}</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_authority_strip() -> None:
    st = _streamlit()
    chips = "".join(
        f'<span class="ovc-chip">{escape(key.replace("_", " "))}: {escape(value)}</span>'
        for key, value in AUTHORITY_BOUNDARY.items()
    )
    st.markdown(f'<div class="ovc-authority-strip">{chips}</div>', unsafe_allow_html=True)
    with st.expander("Full machine-readable authority boundary", expanded=False):
        st.json(AUTHORITY_BOUNDARY)


def render_header(context: Mapping[str, Any]) -> None:
    st = _streamlit()
    left, right = st.columns([5, 1])
    with left:
        st.title("OVC Research Console")
        st.caption("RC-WP1 · design system, shell and navigation · fixture-only local presentation")
    with right:
        st.markdown("<div style='height:0.45rem'></div>", unsafe_allow_html=True)
        st.markdown('<span class="ovc-local-badge">LOCAL · NO DEPLOY</span>', unsafe_allow_html=True)
    render_context_bar(context)
    render_authority_strip()


def render_active_route(route_id: str, fixture_mode: str) -> None:
    route = get_route(route_id)
    fixture = fixture_for_route(route.route_id, fixture_mode)
    render_fixture_surface(fixture)


def render_footer() -> None:
    st = _streamlit()
    st.markdown(
        '<div class="ovc-footer">OVC Research Console v0.2 · local read-only derived surface · '
        'live v0.2 projections denied pending RC-G2 · research writes denied pending separate gate</div>',
        unsafe_allow_html=True,
    )

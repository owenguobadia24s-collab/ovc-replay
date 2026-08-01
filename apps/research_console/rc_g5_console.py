from __future__ import annotations

from html import escape
from typing import Any, Mapping

from apps.research_console import shell as base_shell
from apps.research_console.c1_fact_assurance import render_c1_fact_assurance
from apps.research_console.c2_sequence_evidence import render_c2_sequence_evidence
from apps.research_console.theme import load_css_text


def _configure_page() -> None:
    st = base_shell._streamlit()
    st.set_page_config(
        page_title="OVC Research Console v0.3",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="collapsed",
        menu_items={
            "Get help": None,
            "Report a bug": None,
            "About": "OVC Research Console v0.3 · local read-only RO2, C1 and RC-G5 C2 sequence-evidence presentation",
        },
    )
    st.markdown(f"<style>{load_css_text()}</style>", unsafe_allow_html=True)


def _render_top_bar(bundle: Mapping[str, Any]) -> None:
    st = base_shell._streamlit()
    context = st.session_state.global_context
    title_col, local_col = st.columns([5.2, 1.0])
    with title_col:
        st.markdown('<div class="ovc-workspace-title">OVC Research Console</div>', unsafe_allow_html=True)
        st.caption("RC-G5 · accepted local read-only RO2, C1 and C2 sequence-evidence presentation")
    with local_col:
        st.markdown('<span class="ovc-local-badge">LOCAL · NO DEPLOY</span>', unsafe_allow_html=True)
    base_shell.render_workspace_tabs()
    st.markdown(
        '<div class="ovc-context-bar">'
        f'<span class="ovc-chip">repo {escape(str(context["repository"]))}</span>'
        f'<span class="ovc-chip">branch {escape(str(context["branch"]))}</span>'
        f'<span class="ovc-chip">source {escape(str(context["source_commit"]))}</span>'
        f'<span class="ovc-chip">model {escape(str(context["read_model_sha256"]))}</span>'
        f'<span class="ovc-chip">fixture {escape(str(bundle["fixture_mode"]))}</span>'
        f'<span class="ovc-chip">state {escape(str(bundle["summary_status"]))}</span>'
        f'<span class="ovc-chip">C1 {escape(str(context.get("c1_availability", "NOT_EVALUATED")))}</span>'
        f'<span class="ovc-chip">C2 seq {escape(str(context.get("c2_sequence_availability", "NOT_EVALUATED")))}</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_authority_strip() -> None:
    st = base_shell._streamlit()
    compact = (
        "READ_ONLY",
        "RO2 + C1 + C2 SEQUENCE",
        "NO ACTIONS",
        "NO WRITE",
        "VALIDATION LOCKED",
        "PD TRACE ONLY",
        "NO MARKET",
        "NO EXECUTION",
    )
    chips = "".join(f'<span class="ovc-chip">{escape(item)}</span>' for item in compact)
    st.markdown(f'<div class="ovc-authority-strip">{chips}</div>', unsafe_allow_html=True)
    with st.expander("Full machine-readable authority boundary", expanded=False):
        st.json(base_shell.AUTHORITY_BOUNDARY)


def _render_footer() -> None:
    base_shell._streamlit().markdown(
        '<div class="ovc-footer">OVC Research Console v0.3 · local read-only RO2, C1 and RC-G5 C2 sequence evidence · '
        'Validation locked · annotation and research writes denied · no selector, threshold, market, probability, risk, '
        'exposure, execution, agent-write, R2-write or remote-deployment authority</div>',
        unsafe_allow_html=True,
    )


def run_console(
    identity: Mapping[str, Any] | None = None,
    *,
    c1_projection: Mapping[str, Any] | None = None,
    c2_sequence_projection: Mapping[str, Any] | None = None,
) -> None:
    """Run the accepted shell with RC-G4 C1 and RC-G5 C2 sequence evidence attached."""

    original_configure_page = base_shell.configure_page
    original_top_bar = base_shell.render_top_bar
    original_authority_strip = base_shell.render_authority_strip
    original_research = base_shell.render_research
    original_footer = base_shell.render_footer
    original_boundary = dict(base_shell.AUTHORITY_BOUNDARY)

    def render_research_with_rc_g5(bundle: Mapping[str, Any]) -> None:
        original_research(bundle)
        render_c1_fact_assurance(c1_projection)
        render_c2_sequence_evidence(c2_sequence_projection)

    base_shell.AUTHORITY_BOUNDARY.clear()
    base_shell.AUTHORITY_BOUNDARY.update(
        {
            "mode": "READ_ONLY",
            "presentation": "ACCEPTED_RO2_RC_G4_C1_AND_RC_G5_C2_SEQUENCE_LOCAL_READ_ONLY",
            "c1_route": "ENABLED_LOCAL_READ_ONLY",
            "c1_authority": "LOCAL_READ_ONLY_C1_PRESENTATION",
            "c2_sequence_route": "ENABLED_LOCAL_READ_ONLY",
            "c2_sequence_authority": "LOCAL_READ_ONLY_C2_SEQUENCE_EVIDENCE_PRESENTATION",
            "annotation_actions": "NONE",
            "validation_consumption": "LOCKED_UNCONSUMED",
            "c2_mutation": "DENIED",
            "pattern_discovery_access": "TRIGGER_TRACE_IDENTITY_ONLY",
            "pattern_discovery_mutation": "DENIED",
            "repository_mutation": "NONE",
            "research_write": "DENIED",
            "selector_mutation": "NONE",
            "threshold_mutation": "NONE",
            "release_activation": "NONE",
            "market_classification": "NONE",
            "probability": "NONE",
            "risk": "NONE",
            "exposure": "NONE",
            "execution": "NONE",
            "agent": "NONE",
            "r2_write": "NONE",
            "deployment": "LOCAL_ONLY_NO_REMOTE_DEPLOY",
        }
    )
    base_shell.configure_page = _configure_page
    base_shell.render_top_bar = _render_top_bar
    base_shell.render_authority_strip = _render_authority_strip
    base_shell.render_research = render_research_with_rc_g5
    base_shell.render_footer = _render_footer
    try:
        base_shell.run_console(identity)
    finally:
        base_shell.configure_page = original_configure_page
        base_shell.render_top_bar = original_top_bar
        base_shell.render_authority_strip = original_authority_strip
        base_shell.render_research = original_research
        base_shell.render_footer = original_footer
        base_shell.AUTHORITY_BOUNDARY.clear()
        base_shell.AUTHORITY_BOUNDARY.update(original_boundary)

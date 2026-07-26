from __future__ import annotations

from html import escape
from typing import Any, Mapping

from apps.research_console.components import (
    render_activity_rows,
    render_drawer,
    render_empty_state,
    render_evidence_card,
    render_health_card,
    render_metric_card,
    status_html,
)
from apps.research_console.fixtures import fixture_bundle, object_index, search_objects
from apps.research_console.state import (
    FIXTURE_MODES,
    SYSTEM_SECTIONS,
    WORKSPACES,
    initialise_mapping,
    select_fixture_mode,
    select_object,
    select_system_section,
    switch_workspace,
    update_context,
)
from apps.research_console.theme import load_css_text

AUTHORITY_BOUNDARY: dict[str, str] = {
    "mode": "READ_ONLY",
    "presentation": "FIXTURE_ONLY_LOCAL",
    "repository_mutation": "NONE",
    "research_write": "DENIED",
    "selector_mutation": "NONE",
    "threshold_mutation": "NONE",
    "release_activation": "NONE",
    "market_classification": "NONE",
    "probability": "NONE",
    "exposure": "NONE",
    "execution": "NONE",
    "agent": "NONE",
    "deployment": "LOCAL_ONLY_NO_REMOTE_DEPLOY",
}

WORKSPACE_META = {
    "OVERVIEW": {"icon": "⌂", "label": "Overview", "question": "What context is represented, what is due, and what is blocked?"},
    "RESEARCH": {"icon": "R", "label": "Research", "question": "What supports, contradicts or changes the selected research context?"},
    "SYSTEM": {"icon": "S", "label": "System", "question": "Which sources, releases, QA and lineage produce the represented state?"},
}


def _streamlit():
    import streamlit as st
    return st


def configure_page() -> None:
    st = _streamlit()
    st.set_page_config(
        page_title="OVC Research Console v0.3",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="collapsed",
        menu_items={"Get help": None, "Report a bug": None, "About": "OVC Research Console v0.3 · local fixture-only read surface"},
    )
    st.markdown(f"<style>{load_css_text()}</style>", unsafe_allow_html=True)


def _rerun() -> None:
    _streamlit().rerun()


def _select_object(object_id: str) -> None:
    st = _streamlit()
    select_object(st.session_state, object_id)
    _rerun()


def render_icon_rail() -> None:
    st = _streamlit()
    st.markdown('<div class="ovc-brand">OVC</div>', unsafe_allow_html=True)
    active = st.session_state.active_workspace
    for workspace in WORKSPACES:
        meta = WORKSPACE_META[workspace]
        suffix = " •" if active == workspace else ""
        if st.button(f"{meta['icon']}{suffix}", key=f"rail::{workspace}", help=meta["label"], use_container_width=True):
            switch_workspace(st.session_state, workspace)
            _rerun()
    st.markdown('<div class="ovc-rail-hint">LOCAL<br>READ ONLY</div>', unsafe_allow_html=True)
    st.divider()
    if st.button("?", key="rail::help", help="Open About in System", use_container_width=True):
        switch_workspace(st.session_state, "SYSTEM")
        select_system_section(st.session_state, "ABOUT")
        _rerun()


def render_workspace_tabs() -> None:
    st = _streamlit()
    columns = st.columns([1, 1, 1, 2.7])
    for index, workspace in enumerate(WORKSPACES):
        meta = WORKSPACE_META[workspace]
        active = st.session_state.active_workspace == workspace
        label = f"{meta['label']}" + ("  ●" if active else "")
        if columns[index].button(label, key=f"tab::{workspace}", use_container_width=True):
            switch_workspace(st.session_state, workspace)
            _rerun()
    columns[3].caption("Exactly three primary workspaces · fourth workspace prohibited without a new contract")


def render_top_bar(bundle: Mapping[str, Any]) -> None:
    st = _streamlit()
    context = st.session_state.global_context
    title_col, local_col = st.columns([5.2, 1.0])
    with title_col:
        st.markdown('<div class="ovc-workspace-title">OVC Research Console</div>', unsafe_allow_html=True)
        st.caption("RC-WP1-v0.3 · design system, unified shell and navigation · fixture-only local presentation")
    with local_col:
        st.markdown('<span class="ovc-local-badge">LOCAL · NO DEPLOY</span>', unsafe_allow_html=True)
    render_workspace_tabs()
    st.markdown(
        '<div class="ovc-context-bar">'
        f'<span class="ovc-chip">repo {escape(str(context["repository"]))}</span>'
        f'<span class="ovc-chip">branch {escape(str(context["branch"]))}</span>'
        f'<span class="ovc-chip">source {escape(str(context["source_commit"]))}</span>'
        f'<span class="ovc-chip">model {escape(str(context["read_model_sha256"]))}</span>'
        f'<span class="ovc-chip">fixture {escape(str(bundle["fixture_mode"]))}</span>'
        f'<span class="ovc-chip">state {escape(str(bundle["summary_status"]))}</span>'
        '</div>', unsafe_allow_html=True,
    )


def render_authority_strip() -> None:
    st = _streamlit()
    compact = ("READ_ONLY", "FIXTURE_ONLY_LOCAL", "NO WRITE", "NO SELECTOR", "NO THRESHOLD", "NO MARKET", "NO EXECUTION")
    chips = "".join(f'<span class="ovc-chip">{escape(item)}</span>' for item in compact)
    st.markdown(f'<div class="ovc-authority-strip">{chips}</div>', unsafe_allow_html=True)
    with st.expander("Full machine-readable authority boundary", expanded=False):
        st.json(AUTHORITY_BOUNDARY)


def render_command_palette(bundle: Mapping[str, Any]) -> None:
    st = _streamlit()
    with st.expander("⌘K / Ctrl+K · Read-only command palette", expanded=bool(st.session_state.command_query)):
        query = st.text_input(
            "Search registered fixture objects",
            value=st.session_state.command_query,
            key="command_palette_input",
            placeholder="Search health, release, gate, evidence or queue object…",
            help="This searches the approved fixture index only. It cannot run commands or mutate sources.",
        )
        st.session_state.command_query = query
        results = search_objects(bundle, query)
        if query and not results:
            render_empty_state("NOT_MATERIALIZED", "No registered fixture object matches the query.", "No navigation or authority change occurs.", "Refine the query or inspect a workspace panel.")
        for index, item in enumerate(results[:8]):
            cols = st.columns([1.5, 1.0, 3.5, 0.8])
            cols[0].write(f"**{item.get('label', item.get('object_id'))}**")
            cols[1].markdown(status_html(str(item.get("status", "BLOCK"))), unsafe_allow_html=True)
            cols[2].caption(str(item.get("object_id")))
            if cols[3].button("Open", key=f"search::{index}::{item.get('object_id')}"):
                _select_object(str(item["object_id"]))


def render_context_controls() -> None:
    st = _streamlit()
    context = st.session_state.global_context
    st.markdown('<div class="ovc-kicker">Represented fixture context</div>', unsafe_allow_html=True)
    columns = st.columns([1.1, 1.5, 1.1, 1.0, 1.0, 1.0, 1.4])
    instrument = columns[0].selectbox("Instrument", ("GBPUSD",), index=0, key="ctx_instrument")
    release_id = columns[1].selectbox("Release", ("FIXTURE.RELEASE.DEVELOPMENT.v0.3", "FIXTURE.RELEASE.DISCOVERY.v0.3"), index=0, key="ctx_release")
    clock = columns[2].selectbox("Clock", ("15M / 2H_A_L", "15M", "2H_A_L"), index=0, key="ctx_clock")
    side = columns[3].selectbox("Side", ("BID", "ASK"), index=0, key="ctx_side")
    mode = columns[4].selectbox("Cutoff", ("PROSPECTIVE", "REVIEW"), index=0 if context["cutoff_mode"] == "PROSPECTIVE" else 1, key="ctx_cutoff")
    fixture_mode = columns[5].selectbox("Fixture", FIXTURE_MODES, index=FIXTURE_MODES.index(st.session_state.fixture_mode), key="ctx_fixture")
    columns[6].text_input("Selected time", value=str(context["selected_time"]), disabled=True, key="ctx_time")
    updates = {"instrument": instrument, "release_id": release_id, "clock": clock, "price_side": side, "cutoff_mode": mode}
    for key, value in updates.items():
        if context.get(key) != value:
            update_context(st.session_state, key, value)
    if st.session_state.fixture_mode != fixture_mode:
        select_fixture_mode(st.session_state, fixture_mode)
        _rerun()


def render_ambient_health(bundle: Mapping[str, Any]) -> None:
    st = _streamlit()
    st.markdown('<div class="ovc-panel-title">Ambient health</div>', unsafe_allow_html=True)
    health = list(bundle.get("health", []))
    if not health:
        render_empty_state("NOT_EVALUATED", "No health signals are present.", "No domain may be shown as PASS.", "Produce explicit domain assertions at a later live-projection gate.")
        return
    for start in range(0, len(health), 3):
        columns = st.columns(3)
        for offset, item in enumerate(health[start:start + 3]):
            with columns[offset]:
                if render_health_card(item, button_key=f"health::{item['object_id']}"):
                    _select_object(str(item["object_id"]))


def render_overview(bundle: Mapping[str, Any]) -> None:
    st = _streamlit()
    st.markdown('<div class="ovc-kicker">Overview workspace</div>', unsafe_allow_html=True)
    st.markdown('<div class="ovc-workspace-title">Operating context</div>', unsafe_allow_html=True)
    st.caption(WORKSPACE_META["OVERVIEW"]["question"])
    metrics = st.columns(4)
    with metrics[0]: render_metric_card("Fixture objects", str(len(bundle.get("objects", []))), "No live projections consumed")
    with metrics[1]: render_metric_card("Health domains", str(len(bundle.get("health", []))), "No-signal is never PASS")
    with metrics[2]: render_metric_card("Release fixtures", str(len(bundle.get("releases", []))), "Inspection only")
    with metrics[3]: render_metric_card("Queue attention", "2 due · 1 censored", "Fixture consequence model")
    render_ambient_health(bundle)
    left, middle, right = st.columns(3)
    with left:
        st.markdown('<div class="ovc-panel-title">Release index</div>', unsafe_allow_html=True)
        releases = list(bundle.get("releases", []))
        if releases:
            st.dataframe(releases, use_container_width=True, hide_index=True)
            if st.button("Inspect development release", key="overview::release"): _select_object("RELEASE.DEV.2025")
        else:
            render_empty_state("NOT_EVALUATED", "No fixture releases are present.", "No release state is inferred.", "Select VALID, WARN or BLOCK fixture mode.")
    with middle:
        st.markdown('<div class="ovc-panel-title">Gate status</div>', unsafe_allow_html=True)
        gates = list(bundle.get("gates", []))
        if gates:
            st.dataframe(gates, use_container_width=True, hide_index=True)
            if st.button("Inspect RC-A1", key="overview::gate"): _select_object("GATE.RC_A1")
        else:
            render_empty_state("NOT_EVALUATED", "No fixture gate packet is represented.", "No gate claim is made.", "Restore the fixture source.")
    with right:
        st.markdown('<div class="ovc-panel-title">Research queue summary</div>', unsafe_allow_html=True)
        queue_items = [item for item in bundle.get("objects", []) if item.get("object_type") == "QUEUE_ITEM"]
        if queue_items:
            for item in queue_items:
                st.markdown(f"{status_html(str(item['status']))} **{escape(str(item['label']))}**", unsafe_allow_html=True)
                st.caption(str(item["summary"]))
            if st.button("Inspect due realization", key="overview::queue"): _select_object("QUEUE.REALIZATION.001")
        else:
            render_empty_state("EXPECTED_EMPTY", "No fixture queue items are present.", "Nothing is due in this fixture condition.", "Select another fixture condition if degraded-state review is required.")


def render_research(bundle: Mapping[str, Any]) -> None:
    st = _streamlit()
    context = st.session_state.global_context
    st.markdown('<div class="ovc-kicker">Research workspace</div>', unsafe_allow_html=True)
    st.markdown('<div class="ovc-workspace-title">Unified research context</div>', unsafe_allow_html=True)
    st.caption(WORKSPACE_META["RESEARCH"]["question"])
    render_context_controls()
    cutoff_class = "ovc-cutoff" if context["cutoff_mode"] == "PROSPECTIVE" else "ovc-post-cutoff"
    cutoff_text = "CUTOFF-SAFE · post-cutoff evidence denied" if context["cutoff_mode"] == "PROSPECTIVE" else "REVIEW · post-cutoff evidence must remain separately labelled"
    st.markdown(f'<div class="ovc-card {cutoff_class}"><b>{escape(cutoff_text)}</b><br><span class="ovc-panel-note">Fixture-only replay at {escape(str(context["selected_time"]))}; no market interpretation authority.</span></div>', unsafe_allow_html=True)
    brief_col, replay_col, queue_col = st.columns([1.25, 1.45, 0.8])
    with brief_col:
        st.markdown('<div class="ovc-panel-title">Research brief</div>', unsafe_allow_html=True)
        if bundle["fixture_mode"] == "EMPTY":
            render_empty_state("NOT_MATERIALIZED", "No research fixture is materialized.", "No structural description is produced.", "Select a non-empty fixture or wait for a later live-research gate.")
        elif bundle["summary_status"] == "BLOCK":
            render_empty_state("BLOCK", "The fixture read-model identity is invalid.", "Research panels fail closed.", "Restore a valid represented identity before review.")
        else:
            st.markdown('<div class="ovc-card"><div class="ovc-card-title">Current state</div><div class="ovc-panel-note">Parallel fixture axes coexist; no winning state or semantic collapse is produced.</div></div>', unsafe_allow_html=True)
            st.markdown('<div class="ovc-card"><div class="ovc-card-title">Change conditions</div><div class="ovc-panel-note">Failure to hold the fixture boundary invalidates the developmental reading.</div></div>', unsafe_allow_html=True)
            st.markdown('<div class="ovc-card"><div class="ovc-card-title">Structural meaning</div><div class="ovc-panel-note">NOT_EVALUATED · no C3, probability or execution claim.</div></div>', unsafe_allow_html=True)
    with replay_col:
        st.markdown('<div class="ovc-panel-title">Replay strip</div>', unsafe_allow_html=True)
        replay = list(bundle.get("replay", []))
        if replay:
            st.line_chart(replay, height=210, use_container_width=True)
            st.caption("Declared fixture horizon; post-cutoff values are absent in PROSPECTIVE mode.")
        else:
            render_empty_state("NOT_MATERIALIZED" if bundle["fixture_mode"] == "EMPTY" else "BLOCK", "Replay fixture is unavailable.", "No market path is shown.", "Restore the fixture or pass a later live-replay gate.")
    with queue_col:
        st.markdown('<div class="ovc-panel-title">Ambient queue</div>', unsafe_allow_html=True)
        queue_items = [item for item in bundle.get("objects", []) if item.get("object_type") == "QUEUE_ITEM"]
        if not queue_items:
            render_empty_state("EXPECTED_EMPTY", "No due fixture work.", "Queue remains empty.", "No action required.")
        for item in queue_items:
            st.markdown(f"{status_html(str(item['status']))} **{escape(str(item['label']))}**", unsafe_allow_html=True)
            st.caption(str(item["summary"]))
            if st.button("Inspect", key=f"research::queue::{item['object_id']}", use_container_width=True): _select_object(str(item["object_id"]))
    st.markdown('<div class="ovc-panel-title">Evidence rail</div>', unsafe_allow_html=True)
    evidence = [item for item in bundle.get("objects", []) if item.get("object_type") == "EVIDENCE"]
    if evidence:
        columns = st.columns(4)
        for index, item in enumerate(evidence):
            with columns[index % 4]:
                if render_evidence_card(item, button_key=f"evidence::{item['object_id']}"): _select_object(str(item["object_id"]))
    else:
        render_empty_state("NOT_MATERIALIZED", "No evidence fixture is materialized.", "Support, contradiction, boundary and null roles are not inferred.", "Select another fixture condition.")


def render_system(bundle: Mapping[str, Any]) -> None:
    st = _streamlit()
    st.markdown('<div class="ovc-kicker">System workspace</div>', unsafe_allow_html=True)
    st.markdown('<div class="ovc-workspace-title">Operational inspection</div>', unsafe_allow_html=True)
    st.caption(WORKSPACE_META["SYSTEM"]["question"])
    columns = st.columns(8)
    for index, section in enumerate(SYSTEM_SECTIONS):
        active = st.session_state.active_system_section == section
        label = section.replace("_", " ").title() + (" •" if active else "")
        if columns[index].button(label, key=f"system::{section}", use_container_width=True):
            select_system_section(st.session_state, section)
            _rerun()
    section = st.session_state.active_system_section
    st.markdown(f'<div class="ovc-panel-title">{escape(section.replace("_", " ").title())}</div>', unsafe_allow_html=True)
    if section == "HEALTH":
        render_ambient_health(bundle)
    elif section == "LINEAGE":
        objects = list(bundle.get("objects", []))
        if objects:
            rows = [{key: item.get(key) for key in ("object_id", "object_type", "status", "authority")} for item in objects]
            st.dataframe(rows, use_container_width=True, hide_index=True)
            selected = st.selectbox("Select fixture object", [item["object_id"] for item in objects])
            if st.button("Open selected object", key="system::lineage::open"): _select_object(str(selected))
        else:
            render_empty_state("NOT_EVALUATED", "No fixture objects are indexed.", "Lineage cannot be inspected.", "Select a non-empty fixture condition.")
    elif section == "CATALOGUE":
        st.dataframe([{"artifact_id": "FIXTURE.CONSOLE.CSS", "availability": "LOCAL_FIXTURE", "authority": "PRESENTATION_ONLY"}, {"artifact_id": "FIXTURE.RC_WP1.PACK", "availability": "LOCAL_FIXTURE", "authority": "GOVERNANCE_SOURCE"}], use_container_width=True, hide_index=True)
    elif section == "RELEASES":
        releases = list(bundle.get("releases", []))
        if releases: st.dataframe(releases, use_container_width=True, hide_index=True)
        else: render_empty_state("NOT_EVALUATED", "No fixture releases are present.", "No release claim is made.", "Select another fixture condition.")
    elif section == "QA_GATES":
        gates = list(bundle.get("gates", []))
        if gates: st.dataframe(gates, use_container_width=True, hide_index=True)
        else: render_empty_state("NOT_EVALUATED", "No gate fixtures are present.", "No assurance claim is made.", "Restore the fixture gate source.")
    elif section == "AUDIT":
        render_activity_rows(bundle.get("activity", []), on_select=_select_object)
    elif section == "CONFIGURATION":
        st.json({"local_only": True, "fixture_only": True, "remote_deploy": "DENIED", "global_context": dict(st.session_state.global_context), "authority": AUTHORITY_BOUNDARY})
    elif section == "ABOUT":
        st.markdown("**OVC Research Console v0.3**")
        st.write("A local, read-only, fixture-only unified shell implemented under RC-A1 authority.")
        st.write("Overview, Research and System are the only primary workspaces. Live projections and research writes remain separately gated.")
        st.code("RC-WP1-v0.3 → RC-G1-v0.3")


def render_activity_stream(bundle: Mapping[str, Any]) -> None:
    st = _streamlit()
    with st.expander("Activity stream · persistent, source-derived and read-only", expanded=bool(st.session_state.activity_open)):
        render_activity_rows(bundle.get("activity", []), on_select=_select_object)


def render_footer() -> None:
    _streamlit().markdown('<div class="ovc-footer">OVC Research Console v0.3 · local fixture-only derived presentation · live projections denied · research writes denied · no selector, threshold, market, probability, exposure or execution authority</div>', unsafe_allow_html=True)


def run_console(identity: Mapping[str, Any] | None = None) -> None:
    st = _streamlit()
    configure_page()
    initialise_mapping(st.session_state, identity)
    bundle = fixture_bundle(st.session_state.fixture_mode)
    index = object_index(bundle)
    rail, main, drawer = st.columns([0.32, 4.7, 1.55], gap="small")
    with rail:
        render_icon_rail()
    with main:
        render_top_bar(bundle)
        render_authority_strip()
        render_command_palette(bundle)
        workspace = st.session_state.active_workspace
        if workspace == "OVERVIEW": render_overview(bundle)
        elif workspace == "RESEARCH": render_research(bundle)
        elif workspace == "SYSTEM": render_system(bundle)
        else: render_empty_state("BLOCK", "The selected workspace is not registered.", "Navigation fails closed.", "Return to Overview.")
        render_activity_stream(bundle)
        render_footer()
    with drawer:
        selected = index.get(st.session_state.selected_object_id)
        render_drawer(selected)
        if st.session_state.drawer_open and st.button("Close detail", key="drawer::close", use_container_width=True):
            select_object(st.session_state, None)
            _rerun()

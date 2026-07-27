from __future__ import annotations

from typing import Any, Mapping


AUTHORITY = {
    "surface": "LOCAL_PATTERN_DISCOVERY_CANDIDATE",
    "views": ["Queue", "Candidate Detail", "Clusters"],
    "research_write": "OPERATOR_GATE_REQUIRED",
    "active_novelty_ranking": "DENIED",
    "semantic_promotion": "DENIED",
    "selector_release_r2": "DENIED",
    "probability_exposure_execution": "NONE",
}


def _streamlit():
    import streamlit as st
    return st


def render_queue(items: list[Mapping[str, Any]]) -> str | None:
    st = _streamlit()
    st.subheader("Review Queue")
    st.caption("Reason-coded C2 candidate windows · derived and non-authoritative")
    if not items:
        st.info("No candidates currently meet the frozen trigger and queue rules.")
        return None
    filters = st.columns(4)
    statuses = sorted({str(item.get("status")) for item in items})
    clocks = sorted({str(item.get("clock")) for item in items})
    status = filters[0].selectbox("Status", ["ALL", *statuses])
    clock = filters[1].selectbox("Clock", ["ALL", *clocks])
    control = filters[2].selectbox("Control", ["ALL", "NONE", "MATCHED_CONTROL", "POPULATION_CONTROL"])
    novelty = filters[3].selectbox("Novelty", ["ALL", "BASELINE_FORMING", "CALIBRATED_SHADOW"])
    selected = []
    for item in items:
        if status != "ALL" and item.get("status") != status:
            continue
        if clock != "ALL" and item.get("clock") != clock:
            continue
        if control != "ALL" and item.get("control_class", "NONE") != control:
            continue
        if novelty != "ALL" and item.get("novelty_state") != novelty:
            continue
        selected.append(item)
    if not selected:
        st.warning("No queue items match the current filters.")
        return None
    rows = [{
        "candidate": item.get("candidate_window_id"),
        "window": f"{item.get('window_start_utc')} → {item.get('window_end_utc')}",
        "trigger": item.get("primary_trigger_reason"),
        "clock": item.get("clock"),
        "quality": item.get("quality_state"),
        "cluster": item.get("nearest_cluster_id"),
        "distance": item.get("nearest_cluster_distance"),
        "novelty": item.get("novelty_badge") or item.get("novelty_state"),
        "control": item.get("control_class"),
    } for item in selected]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    return st.selectbox("Open candidate", [str(item["candidate_window_id"]) for item in selected])


def render_candidate_detail(detail: Mapping[str, Any]) -> None:
    st = _streamlit()
    st.subheader("Candidate Detail")
    st.warning(str(detail.get("authority_banner")))
    summary = detail.get("summary", {})
    metrics = st.columns(4)
    metrics[0].metric("Clock", str(summary.get("clock")))
    metrics[1].metric("Quality", str(summary.get("quality_state")))
    metrics[2].metric("Nearest cluster", str(summary.get("nearest_cluster_id") or "UNASSIGNED"))
    metrics[3].metric("Distance", str(summary.get("nearest_cluster_distance") or "N/A"))
    strip = detail.get("price_strip", {})
    if strip.get("status") == "AVAILABLE":
        st.caption("Lightweight exact-OPT-A context strip")
        chart_rows = [{"time": row.get("bar_end_utc"), "close": row.get("close")} for row in strip.get("bars", ())]
        st.line_chart(chart_rows, x="time", y="close")
        st.json(strip.get("markers", {}), expanded=False)
    else:
        st.info("Price strip: NOT_AVAILABLE_SOURCE_UNRESOLVED")
    st.markdown("**Trigger-time explanation**")
    st.json(detail.get("trigger_explanation", {}), expanded=True)
    with st.expander("Five-axis transition timeline", expanded=True):
        st.dataframe(list(detail.get("timeline", ())), use_container_width=True, hide_index=True)
    with st.expander("Fingerprint and similarity", expanded=False):
        st.json(detail.get("fingerprint", {}))
        st.dataframe(list(detail.get("neighbours", ())), use_container_width=True, hide_index=True)
    with st.expander("Immutable source lineage", expanded=False):
        st.json(detail.get("source_lineage", {}))
    st.markdown("**Review action candidate**")
    st.selectbox("Evidence class", list(detail.get("permitted_review_classes", ())))
    st.text_area("Factual observation", placeholder="Describe what C2 represents faithfully or misses.")
    st.text_area("Limitation / next bounded question")
    st.button("Freeze evidence record", disabled=True, help="PD-G4 operator approval is required before canonical evidence writes are enabled.")


def render_clusters(view: Mapping[str, Any]) -> None:
    st = _streamlit()
    st.subheader("Clusters")
    st.warning(str(view.get("authority_banner")))
    st.caption(f"Cluster version {view.get('cluster_version_id')} · {view.get('build_status')} · input {view.get('input_count')}")
    clusters = list(view.get("clusters", ()))
    if not clusters:
        st.info("No provisional clusters are available for this partition.")
        return
    st.dataframe([{
        "cluster": item.get("cluster_id"),
        "status": item.get("status"),
        "members": item.get("member_count"),
        "medoid": item.get("medoid_id"),
        "dispersion": item.get("dispersion"),
        "outliers": len(item.get("outlier_ids", ())),
    } for item in clusters], use_container_width=True, hide_index=True)
    selected_id = st.selectbox("Inspect cluster", [str(item.get("cluster_id")) for item in clusters])
    selected = next(item for item in clusters if item.get("cluster_id") == selected_id)
    st.json(selected)
    st.caption("Permitted: flag assignment, propose split/merge, restrict or reject. Archetype promotion is prohibited.")


def render_pattern_discovery_app(bundle: Mapping[str, Any]) -> None:
    st = _streamlit()
    st.set_page_config(page_title="OVC C2 Pattern Discovery", page_icon="◈", layout="wide")
    st.title("OVC C2 Pattern Discovery")
    st.caption("Simple local research triage · Queue → Candidate Detail → Clusters")
    st.json(AUTHORITY, expanded=False)
    queue_tab, detail_tab, cluster_tab = st.tabs(["Queue", "Candidate Detail", "Clusters"])
    with queue_tab:
        selected = render_queue(list(bundle.get("queue_items", ())))
    details = bundle.get("candidate_details", {})
    with detail_tab:
        selected_id = selected or next(iter(details), None)
        if selected_id and selected_id in details:
            render_candidate_detail(details[selected_id])
        else:
            st.info("Select a candidate from the Queue.")
    with cluster_tab:
        cluster_view = bundle.get("cluster_view")
        if cluster_view:
            render_clusters(cluster_view)
        else:
            st.info("No ClusterVersion projection is available.")


if __name__ == "__main__":
    from apps.research_console.pattern_discovery_fixtures import pattern_discovery_fixture_bundle
    render_pattern_discovery_app(pattern_discovery_fixture_bundle())

from __future__ import annotations

from typing import Any, Mapping, Sequence

from apps.research_console.pattern_discovery_corr2 import render_exact_review_context
from ovc.research_operations.prospective_source.authority import (
    AuthoritySnapshot,
    authority_from_mapping,
    load_repository_authority_snapshot,
)

DEFAULT_AUTHORITY = AuthoritySnapshot()
AUTHORITY = {
    "surface": "LOCAL_PATTERN_DISCOVERY_CANDIDATE",
    "views": ["Queue", "Candidate Detail", "Clusters"],
    "research_write": "OPERATOR_GATE_REQUIRED",
    "active_novelty_ranking": "DENIED",
    "semantic_promotion": "DENIED",
    "selector_release_r2": "DENIED",
    "probability_exposure_execution": "NONE",
}
PILOT_BANNER = "PILOT_ONLY · NON_PROMOTABLE · TIME_GATED_REPLAY · GAPPED_SOURCE"
CORRECTION_BANNER = "C1C-G5-CORR2 · STRUCTURED DEFERRED-OBJECT REVIEW ONLY · C2 AND CANONICAL AUTHORITY UNCHANGED"
REVIEW_DISPOSITIONS = [
    "WORKFLOW_ACCEPTED",
    "FLAG_WORKFLOW_DEFECT",
    "FLAG_UI_FRICTION",
    "DEFER_PILOT_OBJECT",
    "REJECT_PILOT_OBJECT",
]


def review_fields_for_disposition(disposition: str) -> tuple[str, ...]:
    fields = {
        "WORKFLOW_ACCEPTED": ("acceptance_basis", "acceptance_criteria", "evidence_references"),
        "FLAG_WORKFLOW_DEFECT": (
            "finding_code", "affected_component", "actual_behavior", "expected_behavior",
            "reproduction_steps", "acceptance_criteria", "evidence_references",
        ),
        "FLAG_UI_FRICTION": (
            "ui_friction_codes", "affected_console_surface", "affected_component", "actual_behavior",
            "expected_behavior", "reproduction_steps", "acceptance_criteria", "evidence_references",
        ),
        "DEFER_PILOT_OBJECT": (
            "finding_code", "resolution_criteria", "next_review_condition", "evidence_references",
        ),
        "REJECT_PILOT_OBJECT": ("finding_code", "structural_basis", "evidence_references"),
    }
    if disposition not in fields:
        raise ValueError(f"unsupported review disposition: {disposition}")
    return fields[disposition]


def _streamlit():
    import streamlit as st
    return st


def render_queue(items: list[Mapping[str, Any]], authority: AuthoritySnapshot | None = None) -> str | None:
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
        "pilot": "PILOT_ONLY" if item.get("pilot_only") else None,
    } for item in selected]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    return st.selectbox("Open candidate", [str(item["candidate_window_id"]) for item in selected])


def _render_structured_review_fields(
    st: Any,
    disposition: str,
    *,
    candidate_window_id: str,
    exact_evidence_references: Sequence[str] = (),
) -> None:
    st.info(CORRECTION_BANNER)
    st.caption("Structured fields are a local review candidate only. No evidence write, replay or canonical append is enabled.")
    fields = review_fields_for_disposition(disposition)
    labels = {
        "finding_code": "Finding / reason code",
        "affected_component": "Affected component",
        "affected_console_surface": "Affected Console surface",
        "actual_behavior": "Actual behavior",
        "expected_behavior": "Expected behavior",
        "reproduction_steps": "Reproduction steps (one per line)",
        "acceptance_criteria": "Acceptance criteria (one per line)",
        "acceptance_basis": "Acceptance basis",
        "resolution_criteria": "Resolution criteria (one per line)",
        "next_review_condition": "Next lawful review condition",
        "structural_basis": "Structural / workflow rejection basis",
        "evidence_references": "Exact evidence references (one per line)",
        "ui_friction_codes": "UI friction codes (PD-UI-…; one per line)",
    }
    multiline = {
        "actual_behavior", "expected_behavior", "reproduction_steps", "acceptance_criteria",
        "acceptance_basis", "resolution_criteria", "next_review_condition", "structural_basis",
        "evidence_references", "ui_friction_codes",
    }
    key_prefix = f"c1c_g5_corr2_{candidate_window_id}_{disposition}"
    for field in fields:
        label = labels[field]
        value = "\n".join(exact_evidence_references) if field == "evidence_references" else ""
        if field in multiline:
            st.text_area(label, value=value, key=f"{key_prefix}_{field}")
        else:
            st.text_input(label, value=value, key=f"{key_prefix}_{field}")


def render_candidate_detail(detail: Mapping[str, Any], authority: AuthoritySnapshot | None = None) -> None:
    st = _streamlit()
    st.subheader("Candidate Detail")
    if detail.get("pilot", {}).get("pilot_only"):
        st.error(str(detail.get("authority_banner") or PILOT_BANNER))
    else:
        st.warning(authority.authority_label if authority is not None else str(detail.get("authority_banner")))
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

    exact_context = render_exact_review_context(st, detail, queue_item=summary)
    candidate_window_id = str(summary.get("candidate_window_id") or "UNKNOWN_CANDIDATE")
    exact_references = tuple(exact_context.get("exact_evidence_references", ())) if exact_context else ()

    st.markdown("**Review action candidate**")
    disposition = st.selectbox("Review disposition", REVIEW_DISPOSITIONS, key=f"review_disposition_{candidate_window_id}")
    st.selectbox("Evidence class", list(detail.get("permitted_review_classes", ())), key=f"evidence_class_{candidate_window_id}")
    st.text_area("Factual observation", placeholder="Describe what C2 represents faithfully or misses.", key=f"observation_{candidate_window_id}")
    st.text_area("Limitation / next bounded question", key=f"limitation_{candidate_window_id}")
    _render_structured_review_fields(
        st,
        disposition,
        candidate_window_id=candidate_window_id,
        exact_evidence_references=exact_references,
    )
    enabled = authority.live_append_enabled if authority is not None else False
    st.button(
        "Freeze evidence record",
        disabled=not enabled,
        help="Canonical append remains disabled for every Pilot Discovery object.",
        key=f"freeze_evidence_{candidate_window_id}",
    )


def render_clusters(view: Mapping[str, Any]) -> None:
    st = _streamlit()
    st.subheader("Clusters")
    if view.get("pilot_only"):
        st.error(str(view.get("authority_banner") or PILOT_BANNER))
    else:
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
        "pilot": "PILOT_ONLY" if item.get("pilot_only") else None,
    } for item in clusters], use_container_width=True, hide_index=True)
    selected_id = st.selectbox("Inspect cluster", [str(item.get("cluster_id")) for item in clusters])
    selected = next(item for item in clusters if item.get("cluster_id") == selected_id)
    st.json(selected)
    st.caption("Permitted: flag assignment, propose split/merge, restrict or reject. Archetype promotion is prohibited.")


def render_pattern_discovery_app(bundle: Mapping[str, Any]) -> None:
    st = _streamlit()
    authority = authority_from_mapping(bundle.get("authority")) if "authority" in bundle else load_repository_authority_snapshot()
    pilot = bundle.get("pilot") if isinstance(bundle.get("pilot"), Mapping) else None
    st.set_page_config(page_title="OVC C2 Pattern Discovery", page_icon="◈", layout="wide")
    st.title("OVC C2 Pattern Discovery")
    st.caption("Simple local research triage · Queue → Candidate Detail → Clusters")
    if pilot:
        st.error(str(pilot.get("banner") or PILOT_BANNER))
        st.caption(
            f"Namespace {pilot.get('identity_namespace')} · research role {pilot.get('research_role')} · "
            f"canonical population {pilot.get('canonical_discovery_population')}"
        )
    st.json({**AUTHORITY, **authority.as_dict(), "research_write": authority.authority_label}, expanded=False)
    queue_tab, detail_tab, cluster_tab = st.tabs(["Queue", "Candidate Detail", "Clusters"])
    with queue_tab:
        selected = render_queue(list(bundle.get("queue_items", ())), authority)
    details = bundle.get("candidate_details", {})
    with detail_tab:
        selected_id = selected or next(iter(details), None)
        if selected_id and selected_id in details:
            candidate_authority = AuthoritySnapshot(**{**authority.__dict__, "candidate_source_resolved": bool(details[selected_id].get("source_lineage"))})
            render_candidate_detail(details[selected_id], candidate_authority)
        else:
            st.info("Select a candidate from the Queue.")
    with cluster_tab:
        cluster_views = list(bundle.get("cluster_views", ()))
        cluster_view = bundle.get("cluster_view")
        if cluster_view:
            render_clusters(cluster_view)
        elif cluster_views:
            selected_cluster_view = st.selectbox("Partition", [str(item.get("cluster_version_id")) for item in cluster_views])
            render_clusters(next(item for item in cluster_views if str(item.get("cluster_version_id")) == selected_cluster_view))
        else:
            st.info("No ClusterVersion projection is available.")


if __name__ == "__main__":
    from apps.research_console.pattern_discovery_fixtures import pattern_discovery_fixture_bundle
    render_pattern_discovery_app(pattern_discovery_fixture_bundle())

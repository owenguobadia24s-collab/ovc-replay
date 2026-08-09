from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping


DEFAULT_TOPOLOGY_PATH = "var/governance/genesis_repository_topology/current/GENESIS_REPOSITORY_TOPOLOGY_READ_MODEL.json"


def _empty_projection(reason: str) -> dict[str, Any]:
    return {
        "schema": "ovc-genesis-repository-topology-console-projection/v1",
        "availability": "NOT_MATERIALIZED",
        "reason": reason,
        "route_state": "LOCAL_READ_ONLY_SYSTEM_SURFACE",
        "authority_effect": "NONE_PRESENTATION_ONLY",
    }


def load_repository_topology(path: str | Path | None = None) -> dict[str, Any]:
    candidate = Path(path or os.environ.get("OVC_GENESIS_REPOSITORY_TOPOLOGY_READ_MODEL", DEFAULT_TOPOLOGY_PATH))
    if not candidate.is_file():
        return _empty_projection("TOPOLOGY_READ_MODEL_NOT_PRESENT")
    try:
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_projection("TOPOLOGY_READ_MODEL_INVALID")
    if value.get("schema") != "ovc-genesis-repository-topology-read-model/v1":
        return _empty_projection("TOPOLOGY_SCHEMA_MISMATCH")
    if value.get("authority_effect") != "NONE_DERIVED_REPLACEABLE_READ_MODEL":
        return _empty_projection("TOPOLOGY_AUTHORITY_BOUNDARY_MISMATCH")
    return dict(value)


def projection_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("schema") != "ovc-genesis-repository-topology-read-model/v1":
        return {
            "availability": str(value.get("availability", "NOT_MATERIALIZED")),
            "route_state": "LOCAL_READ_ONLY_SYSTEM_SURFACE",
            "topology_sha256": "NOT_EVALUATED",
            "source_commit": "NOT_EVALUATED",
            "programme_count": 0,
            "component_count": 0,
            "anomaly_count": 0,
            "authority_effect": "NONE_PRESENTATION_ONLY",
        }
    portfolio = dict(value.get("portfolio", {}))
    return {
        "availability": "AVAILABLE",
        "route_state": "LOCAL_READ_ONLY_SYSTEM_SURFACE",
        "topology_sha256": str(value.get("topology_sha256", "NOT_EVALUATED")),
        "source_commit": str(portfolio.get("source_commit", "NOT_EVALUATED")),
        "programme_count": int(portfolio.get("programme_count", 0)),
        "component_count": int(portfolio.get("component_count", 0)),
        "anomaly_count": int(portfolio.get("anomaly_count", 0)),
        "authority_effect": "NONE_PRESENTATION_ONLY",
    }


def _bounded_rows(rows: Any, limit: int = 250) -> list[Any]:
    if not isinstance(rows, list):
        return []
    return rows[:limit]


def render_repository_topology_surface(value: Mapping[str, Any]) -> None:
    import streamlit as st

    identity = projection_identity(value)
    st.markdown('<div class="ovc-panel-title">Genesis repository topology · read only</div>', unsafe_allow_html=True)
    st.caption("Derived repository/governance topology. Programme Genesis remains canonical; no graph interaction can mutate source authority.")
    if identity["availability"] != "AVAILABLE":
        st.info(f"Repository topology is not materialized: {value.get('reason', 'NOT_EVALUATED')}.")
        st.caption("Generate the GRT read model locally; no source state is inferred or repaired by this surface.")
        return

    metrics = st.columns(4)
    metrics[0].metric("Programmes", identity["programme_count"])
    metrics[1].metric("Components", identity["component_count"])
    metrics[2].metric("Anomalies", identity["anomaly_count"])
    metrics[3].metric("Topology", identity["topology_sha256"][:12])
    st.caption(f"source {identity['source_commit']} · local read-only System surface · progressive disclosure")

    view = st.selectbox(
        "Topology view",
        (
            "Portfolio View",
            "Programme View",
            "Component View",
            "Dependency View",
            "Authority View",
            "Implementation-State View",
            "Release/Evidence View",
            "Anomaly / Health View",
            "Historical / Supersession View",
            "Commit-to-commit Diff View",
        ),
        key="grt::view",
    )
    if view == "Portfolio View":
        st.json(value.get("portfolio", {}), expanded=False)
        st.json(value.get("health_summary", {}), expanded=False)
    elif view == "Programme View":
        rows = _bounded_rows(value.get("programme_component_crosswalk", []))
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No programme/component crosswalk rows are materialized.")
    elif view == "Component View":
        rows = _bounded_rows(value.get("components", []))
        if rows:
            options = [str(row.get("component_id")) for row in rows]
            selected = st.selectbox("Component", options, key="grt::component")
            row = next(item for item in rows if str(item.get("component_id")) == selected)
            st.json(row, expanded=False)
            incoming = [edge for edge in value.get("component_dependencies", []) if edge.get("to_id") == selected]
            outgoing = [edge for edge in value.get("component_dependencies", []) if edge.get("from_id") == selected]
            st.caption(f"incoming {len(incoming)} · outgoing {len(outgoing)}")
        else:
            st.info("No component rows are materialized.")
    elif view == "Dependency View":
        st.caption("Authoritative programme-dependency references and derived implementation dependencies are deliberately separate.")
        st.dataframe(_bounded_rows(value.get("programme_dependencies", [])), use_container_width=True, hide_index=True)
        st.dataframe(_bounded_rows(value.get("component_dependencies", [])), use_container_width=True, hide_index=True)
    elif view == "Authority View":
        st.dataframe(_bounded_rows(value.get("authority_projection", [])), use_container_width=True, hide_index=True)
        st.caption("This is a source-linked projection; it grants no authority.")
    elif view == "Implementation-State View":
        st.dataframe(_bounded_rows(value.get("implementation_projection", [])), use_container_width=True, hide_index=True)
    elif view == "Release/Evidence View":
        st.dataframe(_bounded_rows(value.get("release_projection", [])), use_container_width=True, hide_index=True)
    elif view == "Anomaly / Health View":
        st.json(value.get("health_summary", {}), expanded=False)
        st.dataframe(_bounded_rows(value.get("anomalies", [])), use_container_width=True, hide_index=True)
    elif view == "Historical / Supersession View":
        st.dataframe(_bounded_rows(value.get("historical_supersession_projection", [])), use_container_width=True, hide_index=True)
    else:
        st.info("Commit-to-commit topology diff is deliberately deferred to post-GRT-G8 GRT-WP10. No Git change is treated as programme approval.")
        st.json({"status": "DEFERRED_PENDING_GRT_WP10", "authority_effect": "NONE_PRESENTATION_ONLY"}, expanded=False)

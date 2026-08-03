from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from apps.research_console import shell as base_shell
from ovc.research_operations.mta.readiness_synthesis import ROUTES, route_payload, validate_reference

DEFAULT_REFERENCE = Path("docs/releases/market-translation-audit-v0-2/mta-g7/MTA_WP7_READINESS_SYNTHESIS_REFERENCE.json")

def load_mta_reference(path: Path | None = None) -> dict[str, Any]:
    source = path or Path(os.environ.get("OVC_MTA_WP7_REFERENCE", str(DEFAULT_REFERENCE)))
    if not source.is_file():
        return {"availability": "NOT_MATERIALIZED", "reason": "MTA_WP7_REFERENCE_UNAVAILABLE"}
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
        validate_reference(value)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"availability": "BLOCK", "reason": f"MTA_WP7_REFERENCE_INVALID:{type(exc).__name__}"}
    value = dict(value)
    value["availability"] = "AVAILABLE"
    return value

def projection_identity(reference: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "availability": reference.get("availability", "NOT_EVALUATED"),
        "programme_id": reference.get("programme_id", "NOT_EVALUATED"),
        "packet_id": reference.get("packet_id", "NOT_EVALUATED"),
        "gate_id": reference.get("gate_id", "NOT_EVALUATED"),
        "route_count": len(reference.get("route_registry", ())),
        "authority": reference.get("authority", {}).get("presentation", "NONE"),
    }

def render_mta_audit_surface(reference: Mapping[str, Any] | None = None) -> None:
    st = base_shell._streamlit()
    source = dict(reference or load_mta_reference())
    st.divider()
    st.markdown('<div class="ovc-panel-title">Market translation audit</div>', unsafe_allow_html=True)
    st.caption("MTA-WP7 · accepted evidence synthesis · local read-only · recommendations prepare plans only")
    if source.get("availability") != "AVAILABLE":
        st.warning(str(source.get("reason", "MTA_WP7_REFERENCE_UNAVAILABLE")))
        return
    route = st.selectbox("Audit route", ROUTES, index=0, key="mta_wp7_route")
    payload = route_payload(source, route)
    st.caption(f"{payload['route']} · {payload['status']} · source {payload['source']}")
    if route == "/readiness":
        rows=[]
        for domain, item in payload["data"].items():
            rows.append({"gate":item["gate_id"],"domain":domain,"recommended_decision":item["recommended_decision"],"effect":item["decision_effect"]})
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.info("Recommendations are evidence for MTA-G8 decisions and grant no activation authority.")
    elif route == "/markers":
        st.dataframe([
            {"rule":name, **counts}
            for name, counts in payload["data"]["rule_counts"].items()
        ], use_container_width=True, hide_index=True)
    else:
        st.json(payload["data"])
    with st.expander("MTA-WP7 authority boundary", expanded=False):
        st.json(payload["authority"])

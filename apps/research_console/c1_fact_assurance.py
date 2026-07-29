from __future__ import annotations

from typing import Any, Mapping

from apps.research_console.c1_projection_source import DOWNSTREAM_AUTHORITY_BANNER


def build_c1_fact_assurance_view(projection: Mapping[str, Any] | None) -> dict[str, Any]:
    """Build a presentation-only view model with permanently separated C1 panels."""

    source = dict(projection or {})
    availability = str(source.get("availability", "NOT_EVALUATED"))
    base = {
        "schema": "ovc-research-console-rc-g4-c1-view/v1",
        "route_id": source.get("route_id", "RESEARCH.C1_FACT_ASSURANCE"),
        "route_state": source.get("route_state", "ENABLED_LOCAL_READ_ONLY"),
        "route_enabled": bool(source.get("route_enabled", True)),
        "availability": availability,
        "authority": "LOCAL_READ_ONLY_C1_PRESENTATION",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "c2_authority": "UNCHANGED",
        "pattern_discovery_authority": "UNCHANGED",
        "read_only": True,
        "writes": "NONE",
    }
    if availability != "AVAILABLE":
        return {
            **base,
            "status": str(source.get("reason", "C1_PROJECTION_NOT_EVALUATED")),
            "source_context": {},
            "fact": {},
            "computability": {},
            "assurance": {},
            "upstream_lineage": {},
            "downstream_trace": {
                "panel_id": "RO3-C1-DOWNSTREAM-TRACE",
                "banner": DOWNSTREAM_AUTHORITY_BANNER,
                "status": "TRACE_NOT_AVAILABLE",
                "child_references": [],
            },
        }

    panels = source.get("panels")
    if not isinstance(panels, Mapping):
        return build_c1_fact_assurance_view({**source, "availability": "NOT_EVALUATED", "reason": "C1_PANEL_SET_UNAVAILABLE"})

    fact = dict(panels.get("fact") or {})
    computability = dict(panels.get("computability") or {})
    assurance = dict(panels.get("assurance") or {})
    upstream = dict(panels.get("upstream_lineage") or {})
    downstream = dict(panels.get("downstream_trace") or {})

    # Presentation separation is explicit in the returned structure. Downstream rows are
    # never copied into the fact panel, and C1 null reasons are never copied downstream.
    fact_view = {
        "panel_id": "RO3-C1-FACT-INSPECTOR",
        "primitive_id": fact.get("primitive_id"),
        "field_name": fact.get("field_name"),
        "inputs": dict(fact.get("inputs") or {}),
        "formula": fact.get("formula"),
        "output": fact.get("output"),
        "unit": fact.get("unit"),
        "domain": dict(fact.get("domain") or {}),
        "null_reason": fact.get("null_reason"),
        "first_valid_time": fact.get("first_valid_time"),
        "c1_record_id": fact.get("c1_record_id"),
        "projection_id": fact.get("projection_id"),
    }
    upstream_view = {
        "panel_id": "RO3-C1-UPSTREAM-LINEAGE",
        "status": upstream.get("status", "LINEAGE_INCOMPLETE"),
        "trace_id": upstream.get("trace_id"),
        "chain": [dict(item) for item in upstream.get("chain", []) if isinstance(item, Mapping)],
        "source_refs": list(upstream.get("source_refs", [])),
        "contract_versions": dict(upstream.get("contract_versions") or {}),
    }
    downstream_view = {
        "panel_id": "RO3-C1-DOWNSTREAM-TRACE",
        "banner": DOWNSTREAM_AUTHORITY_BANNER,
        "status": downstream.get("status", "TRACE_NOT_AVAILABLE"),
        "child_references": [
            dict(item) for item in downstream.get("child_references", []) if isinstance(item, Mapping)
        ],
        "sorting": "IDENTITY_ONLY_NO_SCORE_OR_PRIORITY",
        "c2_authority": "UNCHANGED",
        "pattern_discovery_authority": "UNCHANGED",
    }
    return {
        **base,
        "status": "READY",
        "source_projection_id": source.get("source_projection_id"),
        "source_logical_sha256": source.get("source_logical_sha256"),
        "source_context": dict(source.get("source_context") or {}),
        "fact": fact_view,
        "computability": {
            "panel_id": "RO3-C1-COMPUTABILITY",
            "status": computability.get("status", "NOT_EVALUATED"),
            "field_name": computability.get("field_name"),
            "null_reason": computability.get("null_reason"),
            "record_emission_consequence": computability.get("record_emission_consequence"),
        },
        "assurance": {
            "panel_id": "RO3-C1-ASSURANCE",
            "status": assurance.get("status", "NOT_EVALUATED"),
            "gate_id": assurance.get("gate_id"),
            "metamorphic_run_id": assurance.get("metamorphic_run_id"),
            "determinism_receipt_id": assurance.get("determinism_receipt_id"),
        },
        "upstream_lineage": upstream_view,
        "downstream_trace": downstream_view,
    }


def render_c1_fact_assurance(projection: Mapping[str, Any] | None) -> None:
    """Render RC-G4 C1 presentation without any write or activation controls."""

    import streamlit as st

    view = build_c1_fact_assurance_view(projection)
    st.markdown('<div class="ovc-panel-title">C1 Fact Assurance · local read only</div>', unsafe_allow_html=True)
    st.caption(
        f"Route {view['route_state']} · authority {view['authority']} · "
        "Validation LOCKED_UNCONSUMED · no writes"
    )
    if view["availability"] != "AVAILABLE":
        st.info(
            "C1 presentation is active but no admissible current projection is available. "
            f"State: {view['status']}. No fact or downstream claim is inferred."
        )
        return

    context = view["source_context"]
    st.markdown(
        "**Source binding:** "
        f"{context.get('role')} · {context.get('c1_release_id')} · "
        f"{context.get('clock')} · {context.get('side')}"
    )
    st.caption(
        f"Manifest {context.get('c1_manifest_sha256')} · projection {view.get('source_projection_id')}"
    )

    fact = view["fact"]
    with st.container(border=True):
        st.markdown("#### Fact inspector")
        st.caption(str(fact["panel_id"]))
        left, right = st.columns([1.15, 0.85])
        with left:
            st.write(f"**Primitive:** {fact.get('primitive_id')}")
            st.write(f"**Field:** {fact.get('field_name')}")
            st.code(str(fact.get("formula") or "NOT_EVALUATED"), language=None)
            st.json(fact.get("inputs") or {})
        with right:
            st.metric("Output", str(fact.get("output")))
            st.write(f"**Unit:** {fact.get('unit')}")
            st.write(f"**Null reason:** {fact.get('null_reason') or 'NONE'}")
            st.write(f"**First valid:** {fact.get('first_valid_time')}")

    computability = view["computability"]
    with st.container(border=True):
        st.markdown("#### Computability")
        st.caption(str(computability["panel_id"]))
        st.json(computability)

    assurance = view["assurance"]
    with st.container(border=True):
        st.markdown("#### Formula assurance")
        st.caption(str(assurance["panel_id"]))
        st.json(assurance)

    upstream = view["upstream_lineage"]
    with st.container(border=True):
        st.markdown("#### Upstream lineage")
        st.caption(str(upstream["panel_id"]))
        st.write(f"**Status:** {upstream['status']}")
        if upstream["chain"]:
            st.dataframe(upstream["chain"], use_container_width=True, hide_index=True)
        else:
            st.info("LINEAGE_INCOMPLETE · no upstream lineage claim is presented.")

    downstream = view["downstream_trace"]
    with st.container(border=True):
        st.markdown("#### Downstream trace")
        st.caption(str(downstream["panel_id"]))
        st.warning(downstream["banner"])
        st.caption("Identity-only references. No score, confidence, priority, tuning or remediation meaning.")
        if downstream["child_references"]:
            st.dataframe(downstream["child_references"], use_container_width=True, hide_index=True)
        else:
            st.info("TRACE_NOT_AVAILABLE · missing references do not imply no downstream effect.")

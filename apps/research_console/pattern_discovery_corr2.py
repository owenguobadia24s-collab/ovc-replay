from __future__ import annotations

from typing import Any, Mapping

from ovc.research_operations.pattern_discovery.corr2_evidence import (
    Corr2EvidenceError,
    build_exact_evidence_context,
)


CORR2_BANNER = "C1C-G5-CORR2 · EXACT READ-ONLY REVIEW CONTEXT · NO REPLAY OR CANONICAL AUTHORITY"


def render_exact_review_context(
    st: Any,
    detail: Mapping[str, Any],
    *,
    queue_item: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    st.info(CORR2_BANNER)
    st.caption(
        "Queue, candidate-detail, fingerprint and source-lineage references are resolved to the exact pilot object. "
        "This panel is read-only and cannot append, promote, select or mutate evidence."
    )
    try:
        context = build_exact_evidence_context(detail, queue_item=queue_item)
    except Corr2EvidenceError as exc:
        st.error(f"Exact review context unavailable: {exc}")
        return None

    st.code("\n".join(context["exact_evidence_references"]), language="text")
    with st.expander("Resolved queue context", expanded=True):
        st.json(context["queue_context"], expanded=True)
    with st.expander("Resolved fingerprint context", expanded=True):
        st.json(context["fingerprint_context"], expanded=True)
    with st.expander("Resolved immutable source lineage", expanded=True):
        st.json(context["source_lineage_context"], expanded=True)
    st.json(context["authority"], expanded=False)
    return context

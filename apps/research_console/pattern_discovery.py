from __future__ import annotations

from typing import Any, Mapping

from apps.research_console import pattern_discovery_base as _base
from apps.research_console.pattern_discovery_base import *  # noqa: F401,F403
from ovc.research_operations.pattern_discovery.review_findings_corr2 import build_corr2_console_rows

CORR2_BANNER = (
    "C1C-G5-CORR2 · EXACT READ-ONLY REVIEW CONTEXT · "
    "C2 AND CANONICAL AUTHORITY UNCHANGED"
)
CORRECTION_BANNER = CORR2_BANNER
_ORIGINAL_RENDER_CANDIDATE_DETAIL = _base.render_candidate_detail


def _render_corr2_context(st: Any, detail: Mapping[str, Any]) -> None:
    rows = build_corr2_console_rows(detail)
    if not rows:
        return
    st.markdown("**C1C-G5-CORR2 exact review context**")
    st.caption(
        "Read-only identity, lineage, fingerprint and structural-comparison references. "
        "No selector, release, canonical append or promotion authority is available."
    )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    fingerprint = detail.get("fingerprint")
    if isinstance(fingerprint, Mapping):
        with st.expander("Fingerprint context", expanded=False):
            st.json(dict(fingerprint))
    neighbours = detail.get("neighbours")
    if isinstance(neighbours, list) and neighbours:
        with st.expander("Nearest structural comparison", expanded=False):
            st.json(neighbours[0])
    else:
        st.caption("Nearest structural comparison: NOT_AVAILABLE_EXPLICIT")


def _render_structured_review_fields(st: Any, disposition: str) -> None:
    st.warning(CORR2_BANNER)
    fields = _base.review_fields_for_disposition(disposition)
    st.text_input(
        "Review notes",
        key="pd_corr2_review_notes",
        disabled=not fields.get("notes", False),
    )
    st.text_input(
        "Finding code",
        key="pd_corr2_finding_code",
        disabled=not fields.get("finding_code", False),
    )
    st.text_input(
        "Affected component",
        key="pd_corr2_affected_component",
        disabled=not fields.get("affected_component", False),
    )
    st.text_input(
        "Affected Console surface",
        key="pd_corr2_affected_console_surface",
        disabled=not fields.get("affected_console_surface", False),
    )
    st.text_area(
        "Actual behavior",
        key="pd_corr2_actual_behavior",
        disabled=not fields.get("actual_behavior", False),
    )
    st.text_area(
        "Expected behavior",
        key="pd_corr2_expected_behavior",
        disabled=not fields.get("expected_behavior", False),
    )
    st.text_area(
        "Reproduction steps",
        key="pd_corr2_reproduction_steps",
        disabled=not fields.get("reproduction_steps", False),
    )
    st.text_area(
        "Evidence references",
        key="pd_corr2_evidence_references",
        disabled=not fields.get("evidence_references", False),
    )
    st.text_area(
        "Acceptance or resolution criteria",
        key="pd_corr2_acceptance_criteria",
        disabled=not (
            fields.get("acceptance_criteria", False)
            or fields.get("resolution_criteria", False)
        ),
    )
    st.text_area(
        "Decision basis or structural basis",
        key="pd_corr2_decision_basis",
        disabled=not (
            fields.get("acceptance_basis", False)
            or fields.get("structural_basis", False)
        ),
    )
    st.text_input(
        "Next review condition",
        key="pd_corr2_next_review_condition",
        disabled=not fields.get("next_review_condition", False),
    )
    st.text_input(
        "UI friction codes",
        key="pd_corr2_ui_friction_codes",
        disabled=not fields.get("ui_friction_codes", False),
    )


def render_candidate_detail(detail: Mapping[str, Any], authority: Mapping[str, Any] | None = None) -> None:
    _ORIGINAL_RENDER_CANDIDATE_DETAIL(detail, authority)
    st = _base.st
    st.markdown("---")
    _render_corr2_context(st, detail)


# Patch the base module so its existing app entrypoint and internal calls use CORR2.
_base.CORRECTION_BANNER = CORR2_BANNER
_ORIGINAL_RENDER_CANDIDATE_DETAIL = _base.render_candidate_detail
_base._render_structured_review_fields = _render_structured_review_fields
_base.render_candidate_detail = render_candidate_detail
render_pattern_discovery_app = _base.render_pattern_discovery_app

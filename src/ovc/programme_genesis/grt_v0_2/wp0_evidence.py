"""Evidence-safe public adapter for GRT2-WP0 reconciliation.

The historical v0.1 anomaly identifier is scoped to one observer output/tree;
it is not the v0.2 logical finding identity.  WP0 therefore reproduces B0 and
records a separate fresh census, but defers lineage, late-discovery and
transition-debt classification to WP2 where BaselineMemberRecord,
GRTFindingRecord and DebtLineageRecord semantics exist.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .wp0 import reconcile as _raw_reconcile
from .wp0 import write_reconciliation_outputs


def _evidence_safe(result: dict[str, Any]) -> dict[str, Any]:
    safe = deepcopy(result)
    b0_members = safe["b0"]["members"]
    current = safe["current_census"]
    current_members = current["members"]

    # Remove the provisional raw-ID labels produced by the bootstrap helper.
    # Cross-tree anomaly IDs are physical observer identities, not lawful v0.2
    # finding lineage.  Their intersection is retained only as a diagnostic.
    current.pop("classification", None)
    b0_ids = {str(row["anomaly_id"]) for row in b0_members}
    current_ids = {str(row["anomaly_id"]) for row in current_members}
    direct_matches = b0_ids & current_ids
    current["lineage_classification"] = {
        "status": "DEFERRED_TO_GRT2_WP2",
        "reason_code": "WP0_ANOMALY_ID_NOT_LOGICAL_FINDING_IDENTITY",
        "direct_anomaly_id_match_count": len(direct_matches),
        "current_only_anomaly_id_count": len(current_ids - b0_ids),
        "b0_only_anomaly_id_count": len(b0_ids - current_ids),
        "mapping_prerequisite": "GRT2_WP2_BASELINE_MEMBER_FINDING_AND_DEBT_LINEAGE_CONTRACTS",
        "authority_effect": "NONE_DIAGNOSTIC_ONLY",
    }
    current["transition_debt_status"] = "NOT_EVALUATED_AT_WP0"

    invariants = safe["invariants"]
    invariants.pop("pre_materialisation_census_has_no_grt2_transition_debt", None)
    invariants["current_census_lineage_not_inferred"] = True
    invariants["transition_debt_classification_deferred_to_wp2"] = True
    return safe


def reconcile(
    repository_root: Path,
    *,
    baseline_commit: str,
    verify_b0_determinism: bool = True,
) -> dict[str, Any]:
    """Return exact B0 evidence plus a non-inferential current census."""
    return _evidence_safe(
        _raw_reconcile(
            repository_root,
            baseline_commit=baseline_commit,
            verify_b0_determinism=verify_b0_determinism,
        )
    )


__all__ = ["reconcile", "write_reconciliation_outputs"]

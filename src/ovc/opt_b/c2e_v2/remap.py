"""Comparison-only legacy-v0.1 to C2E-v0.2 remap evidence."""
from __future__ import annotations

from typing import Any, Sequence

from .models import build_record


def build_legacy_remap(*, legacy_episode_ids: Sequence[str], v2_episode_ids: Sequence[str], from_boundary_pack_id: str = "MG-C2E-BOUNDARY-v0.1", to_boundary_pack_id: str, mapping_type: str, first_valid_time: str) -> dict[str, Any]:
    if not legacy_episode_ids:
        raise ValueError("LEGACY_EPISODE_IDS_REQUIRED")
    if any(not str(item).startswith("C2E.EP.") for item in legacy_episode_ids):
        raise ValueError("LEGACY_EPISODE_ID_NAMESPACE_REQUIRED")
    if any(str(item).startswith("C2E.EP.") for item in v2_episode_ids):
        raise ValueError("LEGACY_ID_RELABEL_AS_V2_DENIED")
    return build_record("remap_record", {
        "from_boundary_pack_id": from_boundary_pack_id,
        "to_boundary_pack_id": to_boundary_pack_id,
        "from_episode_ids": sorted({str(item) for item in legacy_episode_ids}),
        "to_episode_ids": sorted({str(item) for item in v2_episode_ids}),
        "mapping_type": mapping_type,
        "comparison_only": True,
        "first_valid_time": first_valid_time,
        "authority": "COMPARISON_ONLY",
    })

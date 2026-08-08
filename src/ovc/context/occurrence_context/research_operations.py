from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .consumers import project_context


def research_operations_projection(context: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return a detached read-only projection for Research Operations inspection.

    The projection has no write, mutation, promotion, selector, publication, or
    execution authority. It never returns a live reference to the source record.
    """
    projected = project_context(context, manifest)
    return {
        "schema": "occurrence_context_research_operations_projection/v0_1",
        "projection": deepcopy(projected),
        "lineage": {
            "occurrence_context_id": str(context["occurrence_context_id"]),
            "logical_hash": str(context["logical_hash"]),
            "first_valid_time": str(context["first_valid_time"]),
        },
        "availability": deepcopy(context.get("availability", {})),
        "reason_codes": deepcopy(context.get("reason_codes", [])),
        "authority_effect": "NONE",
        "write_authority": "NONE",
    }

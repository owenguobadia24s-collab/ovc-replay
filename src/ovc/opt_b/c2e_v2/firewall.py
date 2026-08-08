"""Fail-closed reverse-dependency firewall for the causal C2E handoff."""
from __future__ import annotations

from typing import Any, Mapping

FORBIDDEN_KEY_TOKENS = (
    "family_id", "cluster_id", "medoid", "distance", "sensitivity",
    "invariant_core", "recurrence", "c2p_annotation", "c2_5", "c25",
    "c3", "outcome", "future_path", "future_bar", "mfe", "mae",
    "probability", "risk", "exposure", "execution", "trade_label",
    "research_queue", "review_disposition", "retrospective_segmentation",
    "optimal_segmentation",
)
FORBIDDEN_VALUE_TOKENS = (
    "FDI", "C2G", "C2.5", "C3_AST", "RETROSPECTIVE_BEST_SEGMENTATION",
)


class FirewallError(ValueError):
    pass


def scan_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            for token in FORBIDDEN_KEY_TOKENS:
                if token in lowered:
                    raise FirewallError(f"DEP_FORBIDDEN_FIELD_CONSUMED:{path}.{key}")
            scan_forbidden(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            scan_forbidden(item, f"{path}[{index}]")
    elif isinstance(value, str):
        upper = value.upper()
        for token in FORBIDDEN_VALUE_TOKENS:
            if token.upper() in upper:
                raise FirewallError(f"DEP_FORBIDDEN_VALUE_CONSUMED:{path}")

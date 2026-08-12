from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any


@dataclass(frozen=True)
class DependencyDecision:
    computability: str
    evidence_status: str
    reason_codes: tuple[str, ...]


_REQUIRED_SOURCE_FIELDS = (
    "source_lineage_envelope_id",
    "source_refs",
    "market_effective_start",
    "first_valid_time",
    "evaluation_cutoff",
    "fixture_partition_id",
    "fixture_structure_key",
    "fixture_step",
    "coordinate_class",
    "identity_defining_geometry",
)


def evaluate_synthetic_source(source: Mapping[str, Any]) -> DependencyDecision:
    missing = [name for name in _REQUIRED_SOURCE_FIELDS if name not in source or source[name] is None]
    if missing:
        return DependencyDecision(
            computability="NOT_EVALUABLE",
            evidence_status="NOT_EVALUABLE",
            reason_codes=tuple(f"C2P_SOURCE_FIELD_MISSING:{name}" for name in sorted(missing)),
        )
    refs = source["source_refs"]
    if not isinstance(refs, (list, tuple)) or not refs or any(not isinstance(x, str) or not x for x in refs):
        return DependencyDecision(
            computability="NOT_EVALUABLE",
            evidence_status="NOT_EVALUABLE",
            reason_codes=("C2P_SOURCE_REFS_INVALID",),
        )
    if source.get("source_available", True) is not True:
        return DependencyDecision(
            computability="SOURCE_UNAVAILABLE",
            evidence_status="SOURCE_UNAVAILABLE",
            reason_codes=("C2P_SOURCE_UNAVAILABLE",),
        )
    return DependencyDecision("AVAILABLE", "AVAILABLE", ())

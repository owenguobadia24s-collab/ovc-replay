from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ovc.research_orchestration.serialization import logical_sha256

from .contracts import ClockIndexedOccurrenceRef, MCACContractError

ALLOWED_PUBLIC_KEYS = frozenset({
    "owner_record_id", "occurrence_ref_id", "clock_coordinate_id", "clock_registry_entry_id",
    "owner_generation_id", "source_authority_ref", "source_binding_id", "representation_ref",
    "representation_id", "representation_generation_id", "representation_first_valid_time",
    "representation_adapter_id", "interval_kind", "interval_start", "interval_end", "effective_time",
    "first_valid_time", "evaluation_cutoff", "continuity_segment_id", "source_gap_state",
    "censoring_state", "missingness_state", "owner_payload_ref", "owner_payload_hash",
    "validation_access_state",
})
FORBIDDEN_KEYS = frozenset({"private_payload", "phase", "state_label", "probability", "risk", "exposure", "trade", "children"})


@dataclass(frozen=True)
class RRSCGComparisonInput:
    occurrence: ClockIndexedOccurrenceRef
    source_record_hash: str
    authority_effect: str = "NONE"


def adapt_rrscg_public_record(record: Mapping[str, Any]) -> RRSCGComparisonInput:
    forbidden = sorted(FORBIDDEN_KEYS.intersection(record))
    if forbidden:
        raise MCACContractError("MCAC_RRSCG_PRIVATE_OR_SEMANTIC_FIELD_REJECTED", ",".join(forbidden))
    unknown = sorted(set(record) - ALLOWED_PUBLIC_KEYS)
    if unknown:
        raise MCACContractError("MCAC_RRSCG_UNKNOWN_OWNER_FIELD_REJECTED", ",".join(unknown))
    occurrence = ClockIndexedOccurrenceRef(**dict(record))
    if occurrence.owner_payload_ref != "OPAQUE_NOT_DEREFERENCEABLE":
        raise MCACContractError("MCAC_OWNER_PAYLOAD_DEREFERENCE_FORBIDDEN", occurrence.owner_record_id)
    return RRSCGComparisonInput(occurrence, logical_sha256(dict(record)))

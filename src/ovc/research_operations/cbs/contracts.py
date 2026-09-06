from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .enums import CORE_COMPARATOR_IDS, Estimand, TemporalClass
from .identity import CBSContractError, seal_object


FORBIDDEN_OWNER_MUTATIONS = frozenset(
    {
        "C2E_PACK_SELECT",
        "C2E_PACK_REPLACE",
        "C2E_EPISODE_REWRITE",
        "C2E_BOUNDARY_SEMANTICS_CHANGE",
        "VALIDATION_CONSUME",
        "CANONICAL_PUBLISH",
    }
)


def build_research_generation(
    *, generation: int, role: str, predecessor_id: str | None, exposure_frontier_id: str
) -> dict[str, Any]:
    if generation < 1 or role not in {"SYNTHETIC", "DEVELOPMENT", "REPLICATION"}:
        raise CBSContractError("CBS_RESEARCH_GENERATION_INVALID")
    return seal_object(
        {
            "schema": "ovc-cbs-research-generation/v0.1",
            "programme_id": "C2E-BOUNDARY-STABILITY-0001",
            "generation": generation,
            "role": role,
            "predecessor_id": predecessor_id,
            "exposure_frontier_id": exposure_frontier_id,
            "authority_effect": "NONE",
        },
        id_field="research_generation_id",
    )


def validate_comparator_registry(registry: Mapping[str, Any]) -> None:
    comparators = registry.get("comparators")
    if not isinstance(comparators, list):
        raise CBSContractError("CBS_COMPARATOR_REGISTRY_INVALID")
    by_id = {str(item.get("id")): item for item in comparators if isinstance(item, Mapping)}
    if not set(CORE_COMPARATOR_IDS) <= set(by_id):
        raise CBSContractError("CBS_MINIMUM_COMPARATOR_ENVELOPE_INCOMPLETE")
    if by_id["B3"].get("causal_admissibility") is not False:
        raise CBSContractError("CBS_RETROSPECTIVE_CAUSAL_ADMISSION_FORBIDDEN")
    if by_id["B9"].get("temporal_class") != TemporalClass.CONTROL.value:
        raise CBSContractError("CBS_CONTROL_CLASS_INVALID")
    for comparator_id in ("B4", "B5", "B6", "B7"):
        if comparator_id in by_id and by_id[comparator_id].get("availability") not in {
            "CONDITIONAL_NOT_ADMITTED", "AVAILABLE", "NOT_EVALUABLE"
        }:
            raise CBSContractError("CBS_CONDITIONAL_COMPARATOR_STATUS_INVALID")


def validate_estimand_identity(record: Mapping[str, Any], expected: Estimand) -> None:
    if record.get("estimand") != expected.value:
        raise CBSContractError("ESTIMAND_CROSSING")
    denominator_id = str(record.get("denominator_id", ""))
    if not denominator_id:
        raise CBSContractError("SUPPORT_UNIVERSE_INCOMPLETE")


def validate_authority_delta(actions: Sequence[str]) -> None:
    forbidden = sorted(set(actions) & FORBIDDEN_OWNER_MUTATIONS)
    if forbidden:
        raise CBSContractError(f"CBS_OWNER_AUTHORITY_VIOLATION:{','.join(forbidden)}")

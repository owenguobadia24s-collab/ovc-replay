from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from .canonical import evidence_frontier_logical_hash, sha256_canonical


class SRICompatibilityError(ValueError):
    pass


_STRUCTURAL_DIMENSIONS = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION")
_REPRESENTATION_CLASSES = frozenset({f"SRI-R{i}" for i in range(1, 10)})
_PROHIBITED_KEYS = frozenset({
    "family_id", "family_ids", "prototype_id", "distance_result", "similarity_result",
    "future_return", "mfe", "mae", "outcome", "outcomes", "validation_label",
    "probability", "risk", "exposure", "trade", "trading", "execution",
})
_METHOD_ID = "METHOD_NEUTRAL_IDENTITY_PROJECTION_v0_1"


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_value(item) for item in value]
    return copy.deepcopy(value)


def _scan_prohibited(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in _PROHIBITED_KEYS:
                raise SRICompatibilityError(f"ESL_SRI_FORBIDDEN_FIELD:{path}.{key}")
            _scan_prohibited(child, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _scan_prohibited(child, f"{path}[{index}]")


@dataclass(frozen=True)
class SRICompatibilityPack:
    adapter_pack_id: str
    version: str
    representation_class: str
    exposed_dimensions: tuple[str, ...]
    omitted_dimensions: tuple[str, ...]
    information_loss_dimensions: tuple[str, ...]
    comparability_domain_id: str
    comparability_generation: str
    context_input_fields: tuple[str, ...] = ()
    context_role: str | None = None
    historical_aliases: tuple[str, ...] = ()
    method_id: str = _METHOD_ID

    def __post_init__(self) -> None:
        if not self.adapter_pack_id or not self.version:
            raise SRICompatibilityError("ESL_SRI_PACK_ID_VERSION_REQUIRED")
        if self.representation_class not in _REPRESENTATION_CLASSES:
            raise SRICompatibilityError("ESL_SRI_REPRESENTATION_CLASS_INVALID")
        if self.method_id != _METHOD_ID:
            raise SRICompatibilityError("ESL_SRI_METHOD_SELECTION_FORBIDDEN")
        exposed = tuple(self.exposed_dimensions)
        omitted = tuple(self.omitted_dimensions)
        if len(set(exposed)) != len(exposed) or len(set(omitted)) != len(omitted):
            raise SRICompatibilityError("ESL_SRI_DIMENSION_DUPLICATE")
        if set(exposed) & set(omitted):
            raise SRICompatibilityError("ESL_SRI_DIMENSION_EXPOSED_AND_OMITTED")
        if set(exposed) | set(omitted) != set(_STRUCTURAL_DIMENSIONS):
            raise SRICompatibilityError("ESL_SRI_DIMENSION_DISCLOSURE_INCOMPLETE")
        if set(self.information_loss_dimensions) != set(omitted):
            raise SRICompatibilityError("ESL_SRI_INFORMATION_LOSS_MUST_MATCH_OMISSIONS")
        if not self.comparability_domain_id or not self.comparability_generation:
            raise SRICompatibilityError("ESL_SRI_COMPARABILITY_BINDING_REQUIRED")
        if self.context_input_fields:
            if self.context_role != "REPRESENTATION_INPUT":
                raise SRICompatibilityError("ESL_SRI_CONTEXT_ROLE_MUST_BE_REPRESENTATION_INPUT")
            if len(set(self.context_input_fields)) != len(self.context_input_fields):
                raise SRICompatibilityError("ESL_SRI_CONTEXT_FIELD_DUPLICATE")
        elif self.context_role is not None:
            raise SRICompatibilityError("ESL_SRI_CONTEXT_ROLE_WITHOUT_FIELDS")


def pack_from_mapping(value: Mapping[str, Any]) -> SRICompatibilityPack:
    raw = dict(value)
    return SRICompatibilityPack(
        adapter_pack_id=str(raw["adapter_pack_id"]),
        version=str(raw["version"]),
        representation_class=str(raw["representation_class"]),
        exposed_dimensions=tuple(str(item) for item in raw["exposed_dimensions"]),
        omitted_dimensions=tuple(str(item) for item in raw["omitted_dimensions"]),
        information_loss_dimensions=tuple(str(item) for item in raw["information_loss_dimensions"]),
        comparability_domain_id=str(raw["comparability_domain_id"]),
        comparability_generation=str(raw["comparability_generation"]),
        context_input_fields=tuple(str(item) for item in raw.get("context_input_fields", [])),
        context_role=raw.get("context_role"),
        historical_aliases=tuple(str(item) for item in raw.get("historical_aliases", [])),
        method_id=str(raw.get("method_id", _METHOD_ID)),
    )


def compile_sri_compatibility_record(
    occurrence: Any,
    pack: SRICompatibilityPack,
    *,
    source_population_id: str,
    context_inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project one frozen StructuralOccurrence into the inactive SRI compatibility surface.

    The adapter deliberately performs no feature selection, normalization, family discovery, distance
    calculation or scientific disposition. It preserves only pack-declared facets and records every
    omission as information loss.
    """
    source = _json_value(occurrence)
    if not isinstance(source, Mapping):
        raise SRICompatibilityError("ESL_SRI_STRUCTURAL_OCCURRENCE_OBJECT_REQUIRED")
    source = dict(source)
    _scan_prohibited(source)
    if source.get("authority_state") != "INACTIVE_CONFORMANCE_ONLY":
        raise SRICompatibilityError("ESL_SRI_SOURCE_AUTHORITY_NOT_INACTIVE")
    occurrence_id = str(source.get("occurrence_record_id") or "")
    if not occurrence_id:
        raise SRICompatibilityError("ESL_SRI_OCCURRENCE_ID_REQUIRED")
    occurrence_pack_id = str(source.get("occurrence_pack_id") or "")
    if not occurrence_pack_id:
        raise SRICompatibilityError("ESL_SRI_OCCURRENCE_PACK_ID_REQUIRED")
    source_domain = str(source.get("comparability_domain_id") or "")
    if source_domain != pack.comparability_domain_id:
        raise SRICompatibilityError("ESL_SRI_COMPARABILITY_DOMAIN_MISMATCH")
    cutoff = str(source.get("evaluation_cutoff") or "")
    first_valid = str(source.get("first_valid_time") or "")
    if not cutoff or not first_valid:
        raise SRICompatibilityError("ESL_SRI_CHRONOLOGY_REQUIRED")
    generations = source.get("source_generation_ids")
    if not isinstance(generations, list) or not generations:
        raise SRICompatibilityError("ESL_SRI_SOURCE_GENERATIONS_REQUIRED")
    frontier = source.get("evidence_frontier")
    if not isinstance(frontier, Mapping):
        raise SRICompatibilityError("ESL_SRI_EVIDENCE_FRONTIER_REQUIRED")
    facets = source.get("facets")
    if not isinstance(facets, list):
        raise SRICompatibilityError("ESL_SRI_FACETS_LIST_REQUIRED")
    by_dimension: dict[str, dict[str, Any]] = {}
    for facet in facets:
        if not isinstance(facet, Mapping):
            raise SRICompatibilityError("ESL_SRI_FACET_OBJECT_REQUIRED")
        row = dict(facet)
        dimension = str(row.get("dimension") or "")
        if dimension not in _STRUCTURAL_DIMENSIONS:
            raise SRICompatibilityError("ESL_SRI_DIMENSION_INVALID:" + dimension)
        if dimension in by_dimension:
            raise SRICompatibilityError("ESL_SRI_DIMENSION_DUPLICATE:" + dimension)
        by_dimension[dimension] = row
    if set(by_dimension) != set(_STRUCTURAL_DIMENSIONS):
        raise SRICompatibilityError("ESL_SRI_SOURCE_DIMENSION_SET_INCOMPLETE")

    supplied_context = _json_value(context_inputs or {})
    if not isinstance(supplied_context, Mapping):
        raise SRICompatibilityError("ESL_SRI_CONTEXT_OBJECT_REQUIRED")
    supplied_context = dict(supplied_context)
    _scan_prohibited(supplied_context, "$.context_inputs")
    declared_context = set(pack.context_input_fields)
    actual_context = set(supplied_context)
    if actual_context - declared_context:
        raise SRICompatibilityError("ESL_SRI_UNDECLARED_CONTEXT_INPUT:" + ",".join(sorted(actual_context - declared_context)))
    if declared_context - actual_context:
        raise SRICompatibilityError("ESL_SRI_DECLARED_CONTEXT_INPUT_MISSING:" + ",".join(sorted(declared_context - actual_context)))

    structural_raw: dict[str, Any] = {}
    missingness: dict[str, str] = {}
    for dimension in pack.exposed_dimensions:
        facet = by_dimension[dimension]
        state = str(facet.get("evidence_state") or "")
        if not state:
            raise SRICompatibilityError("ESL_SRI_FACET_EVIDENCE_STATE_REQUIRED:" + dimension)
        missingness[dimension] = state
        structural_raw[dimension] = {
            "evidence_state": state,
            "source_ref_ids": sorted(str(item) for item in facet.get("source_ref_ids", [])),
            "value": _json_value(facet.get("value")),
            "reason_codes": sorted(str(item) for item in facet.get("reason_codes", [])),
        }

    omissions = [
        {
            "dimension": dimension,
            "source_evidence_state": str(by_dimension[dimension].get("evidence_state") or ""),
            "reason_code": "PACK_DECLARED_OMISSION",
        }
        for dimension in pack.omitted_dimensions
    ]
    payload = {
        "schema": "ovc-esl-sri-compatibility-record/v1",
        "representation_pack_id": pack.adapter_pack_id,
        "representation_pack_version": pack.version,
        "representation_class": pack.representation_class,
        "representation_method": {
            "method_id": pack.method_id,
            "method_neutral": True,
            "scientific_selection": "NONE",
        },
        "source_population_id": source_population_id,
        "source_occurrence": {
            "occurrence_record_id": occurrence_id,
            "occurrence_pack_id": occurrence_pack_id,
            "source_generation_ids": sorted(str(item) for item in generations),
            "evidence_frontier_logical_hash": evidence_frontier_logical_hash(dict(frontier)),
            "first_valid_time": first_valid,
            "evaluation_cutoff": cutoff,
        },
        "structural_raw": structural_raw,
        "structural_derived": {},
        "structural_normalized": {},
        "comparison_only": {},
        "missingness": missingness,
        "omissions": omissions,
        "information_loss": {
            "declared": bool(pack.information_loss_dimensions),
            "omitted_dimensions": list(pack.information_loss_dimensions),
            "implicit_imputation": "PROHIBITED",
        },
        "context": {
            "role": pack.context_role,
            "declared_fields": list(pack.context_input_fields),
            "values": supplied_context,
        },
        "comparability": {
            "comparability_domain_id": pack.comparability_domain_id,
            "generation": pack.comparability_generation,
        },
        "historical_crosswalk_aliases": sorted(pack.historical_aliases),
        "authority": {
            "authority_state": "INACTIVE_CONFORMANCE_ONLY",
            "representation_activation": "NONE",
            "method_selection": "NONE",
            "family_promotion": "NONE",
            "semantic_promotion": "NONE",
            "validation_consumption": "LOCKED_UNCONSUMED",
        },
    }
    if not source_population_id:
        raise SRICompatibilityError("ESL_SRI_SOURCE_POPULATION_ID_REQUIRED")
    identity = dict(payload)
    logical_hash = sha256_canonical(identity)
    return {**payload, "representation_id": "sri1:" + logical_hash, "logical_hash": logical_hash}

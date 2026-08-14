from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

from .canonical import sha256_canonical


class ESLReadModelError(ValueError):
    pass


SECTION_TYPES = frozenset({
    "STRUCTURAL_OCCURRENCE",
    "EVIDENCE_FRONTIER",
    "SRI_REPRESENTATION",
    "ORGANISATION_EVIDENCE",
    "CONSTRAINT_EVIDENCE",
    "TERM_QUALIFICATION",
    "C3_STATEMENT_AST",
    "C3_RENDER",
    "RESEARCH_HANDOFF",
    "AUTHORITY",
    "LINEAGE",
})

_FORBIDDEN_FRONTEND_SCIENCE_KEYS = frozenset({
    "candidate_strength_score",
    "scientific_score",
    "information_score",
    "best_profile",
    "winner",
    "probability",
    "expected_return",
    "risk",
    "exposure",
    "trade_direction",
    "execution_instruction",
})


def _copy(value: Any) -> Any:
    return copy.deepcopy(value)


def _scan_forbidden(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            if key_text in _FORBIDDEN_FRONTEND_SCIENCE_KEYS:
                raise ESLReadModelError(f"ESL_READ_MODEL_FRONTEND_SCIENCE_FORBIDDEN:{path}.{key}")
            _scan_forbidden(child, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _scan_forbidden(child, f"{path}[{index}]")


def build_read_model_section(
    *,
    section_type: str,
    source_ref: str,
    source_owner: str,
    source_generation: str,
    evaluation_cutoff: str,
    first_valid_time: str,
    evidence_state: str,
    authority_state: str,
    lineage_refs: Sequence[Any],
    payload: Mapping[str, Any],
    denominator: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    kind = str(section_type)
    if kind not in SECTION_TYPES:
        raise ESLReadModelError("ESL_READ_MODEL_SECTION_TYPE_INVALID")
    body = _copy(payload)
    if not isinstance(body, Mapping):
        raise ESLReadModelError("ESL_READ_MODEL_PAYLOAD_MAPPING_REQUIRED")
    _scan_forbidden(body)
    denominator_payload = None if denominator is None else _copy(denominator)
    if denominator_payload is not None:
        if not isinstance(denominator_payload, Mapping):
            raise ESLReadModelError("ESL_READ_MODEL_DENOMINATOR_MAPPING_REQUIRED")
        if "denominator" not in denominator_payload and "eligible_universe" not in denominator_payload:
            raise ESLReadModelError("ESL_READ_MODEL_DENOMINATOR_EXPLICIT_REQUIRED")
    lineage = sorted({str(x) for x in lineage_refs})
    section = {
        "schema": "ovc-esl-read-model-section/v1",
        "section_type": kind,
        "source_ref": str(source_ref),
        "source_owner": str(source_owner),
        "source_generation": str(source_generation),
        "evaluation_cutoff": str(evaluation_cutoff),
        "first_valid_time": str(first_valid_time),
        "evidence_state": str(evidence_state),
        "denominator": denominator_payload,
        "authority_state": str(authority_state),
        "lineage_refs": lineage,
        "payload": body,
        "calculation_policy": "SOURCE_FIELDS_ONLY",
        "writable": False,
        "authority_effect": "NONE",
    }
    section["section_id"] = "eslrmsec1:" + sha256_canonical(section)
    return section


def build_esl_read_model(*, sections: Sequence[Mapping[str, Any]], source_frontier_ref: str, console_authority: str = "READ_ONLY") -> dict[str, Any]:
    if console_authority not in {"READ_ONLY", "FIXTURE_ONLY_LOCAL_READ_ONLY", "GET_ONLY"}:
        raise ESLReadModelError("ESL_READ_MODEL_CONSOLE_AUTHORITY_NOT_READ_ONLY")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in sections:
        item = _copy(raw)
        if item.get("schema") != "ovc-esl-read-model-section/v1" or item.get("writable") is not False:
            raise ESLReadModelError("ESL_READ_MODEL_SECTION_INVALID")
        _scan_forbidden(item.get("payload", {}))
        section_id = str(item.get("section_id", ""))
        if not section_id or section_id in seen:
            raise ESLReadModelError("ESL_READ_MODEL_SECTION_ID_INVALID")
        seen.add(section_id)
        items.append(item)
    items.sort(key=lambda item: (str(item["section_type"]), str(item["source_ref"])))
    payload = {
        "schema": "ovc-esl-read-model/v1",
        "source_frontier_ref": str(source_frontier_ref),
        "console_authority": console_authority,
        "sections": items,
        "scientific_calculation_location": "BACKEND_SOURCE_OBJECTS_ONLY",
        "frontend_scientific_calculation": "FORBIDDEN",
        "mutation_routes": [],
        "replaceable_projection": True,
        "authority_effect": "NONE",
    }
    payload["read_model_id"] = "eslrm1:" + sha256_canonical(payload)
    return payload


def assert_projection_fidelity(*, read_model: Mapping[str, Any], source_sections: Sequence[Mapping[str, Any]]) -> None:
    expected = {str(item["section_id"]): sha256_canonical(item) for item in source_sections}
    actual = {str(item["section_id"]): sha256_canonical(item) for item in read_model.get("sections", [])}
    if expected != actual:
        raise ESLReadModelError("ESL_READ_MODEL_FIDELITY_MISMATCH")
    if read_model.get("mutation_routes"):
        raise ESLReadModelError("ESL_READ_MODEL_MUTATION_ROUTE_FORBIDDEN")

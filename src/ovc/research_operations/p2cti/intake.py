from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .identity import control_record_id

_ROOT = Path(__file__).resolve().parents[4]
_OPERATIONAL = json.loads((_ROOT / "registries/research_operations/p2cti/P2CTI_OPERATIONAL_VOCABULARY_REGISTRY_v0_1.json").read_text(encoding="utf-8"))
_DMRP = json.loads((_ROOT / "registries/research_operations/DMRP_PATH2_INTAKE_VOCABULARY_CONFORMANCE_EXT_v0_1.json").read_text(encoding="utf-8"))
_REASON_REGISTRY = json.loads((_ROOT / "registries/research_operations/p2cti/P2CTI_REASON_CODE_REGISTRY_v0_1.json").read_text(encoding="utf-8"))

_VISIBILITY = frozenset(_OPERATIONAL["visibility_states"])
_DMRP_DESIGN = frozenset(_DMRP["design_vocabulary"])
_DMRP_MAPPING = {row["design"]: row for row in _DMRP["mappings"]}
_REASON_CODES = frozenset(row["code"] for row in _REASON_REGISTRY["reason_codes"])
_CAPTURE = frozenset({"SYNTHETIC_ONLY", "CAPTURED_REFERENCE_ONLY", "UNRESOLVED_SOURCE", "QUARANTINED"})
_SOURCE_FIELDS = frozenset({"source_id", "source_kind", "source_locator", "content_sha256", "authority_refs", "scientific_payload_copied"})
_FORBIDDEN_KEY_FRAGMENTS = (
    "probability", "risk", "exposure", "trade", "execution", "candidate_freeze",
    "candidatefreeze", "theory_truth", "truth_score", "theory_value", "alpha_score",
    "scientific_score", "promotion_score",
)


class IntakeValidationError(ValueError):
    pass


def _digest(value: str, field: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise IntakeValidationError(f"{field} must be lowercase SHA-256")
    return value


def _strings(values: Sequence[str], field: str, *, allow_empty: bool = False) -> list[str]:
    if type(values) not in (list, tuple) or any(type(v) is not str or not v for v in values):
        raise IntakeValidationError(f"{field} must contain non-empty strings")
    result = sorted(set(values))
    if len(result) != len(values):
        raise IntakeValidationError(f"{field} must be unique")
    if not result and not allow_empty:
        raise IntakeValidationError(f"{field} must not be empty")
    return result


def _reasons(values: Sequence[str]) -> list[str]:
    reasons = _strings(values, "reason_codes", allow_empty=True)
    unknown = set(reasons) - _REASON_CODES
    if unknown:
        raise IntakeValidationError(f"unknown reason codes: {sorted(unknown)}")
    return reasons


def _reject_authority_payload(value: Any, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in _FORBIDDEN_KEY_FRAGMENTS):
                raise IntakeValidationError(f"forbidden decision-bearing intake field: {path}.{key}")
            _reject_authority_payload(item, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _reject_authority_payload(item, f"{path}[{index}]")


def exact_source_reference(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or frozenset(raw) != _SOURCE_FIELDS:
        raise IntakeValidationError("source_ref must use the exact reference-only shape")
    result = dict(raw)
    for field in ("source_id", "source_kind", "source_locator"):
        if type(result[field]) is not str or not result[field]:
            raise IntakeValidationError(f"source_ref {field} is invalid")
    _digest(result["content_sha256"], "source_ref.content_sha256")
    result["authority_refs"] = _strings(result["authority_refs"], "source_ref.authority_refs")
    if result["scientific_payload_copied"] is not False:
        raise IntakeValidationError("owner scientific payload must remain reference-only")
    return {key: result[key] for key in sorted(result)}


def _frontier(source_frontier_id: str) -> str:
    if type(source_frontier_id) is not str or not source_frontier_id.startswith("p2cti:frontier:"):
        raise IntakeValidationError("source_frontier_id must be a P2CTI frontier")
    _digest(source_frontier_id.rsplit(":", 1)[1], "source_frontier_id")
    return source_frontier_id


def _record(*, object_type: str, source_frontier_id: str, identity: Mapping[str, Any], payload: Mapping[str, Any]) -> dict[str, Any]:
    frontier = _frontier(source_frontier_id)
    _reject_authority_payload(payload)
    record_id = control_record_id(object_type=object_type, source_frontier=frontier, identity_payload=identity)
    body = {
        "schema_family": "P2CTI_CONTROL",
        "schema_version": "0.1",
        "object_type": object_type,
        "record_id": record_id,
        "source_frontier_id": frontier,
        "payload": dict(payload),
        "authority_effect": "NONE",
    }
    return {**body, "content_sha256": canonical_sha256(body)}


def build_theory_seed(
    *,
    source_frontier_id: str,
    seed_key: str,
    title: str,
    source_ref: Mapping[str, Any],
    visibility_state: str = "RESTRICTED",
    capture_state: str = "SYNTHETIC_ONLY",
) -> dict[str, Any]:
    if type(seed_key) is not str or not seed_key or type(title) is not str or not title:
        raise IntakeValidationError("seed_key and title are required")
    if visibility_state not in _VISIBILITY:
        raise IntakeValidationError("visibility_state is outside the closed registry")
    if capture_state not in _CAPTURE:
        raise IntakeValidationError("capture_state is outside the WP5 closed surface")
    source = exact_source_reference(source_ref)
    seed_identity = {
        "seed_key": seed_key,
        "title": title,
        "source_ref": source,
        "visibility_state": visibility_state,
        "capture_state": capture_state,
    }
    seed_id = f"p2cti:seed:{canonical_sha256(seed_identity)}"
    payload = {
        "seed_id": seed_id,
        "title": title,
        "source_ref": source,
        "visibility_state": visibility_state,
        "capture_state": capture_state,
        "owner_object_created": False,
        "write_activation": False,
        "scientific_effect": "NONE",
        "candidate_effect": "NONE",
    }
    return _record(object_type="THEORY_SEED", source_frontier_id=source_frontier_id, identity={"seed_id": seed_id}, payload=payload)


def build_intake_triage(
    *,
    source_frontier_id: str,
    seed_or_theory_ref: str,
    design_disposition: str,
    reason_codes: Sequence[str],
) -> dict[str, Any]:
    if type(seed_or_theory_ref) is not str or not seed_or_theory_ref:
        raise IntakeValidationError("seed_or_theory_ref is required")
    if design_disposition not in _DMRP_DESIGN:
        raise IntakeValidationError("design_disposition is outside the ratified DMRP intake vocabulary")
    mapping = _DMRP_MAPPING[design_disposition]
    mapped = mapping.get("implementation")
    disposition = mapped if type(mapped) is str and mapped else "UNMAPPED_REVIEW_REQUIRED"
    reasons = _reasons(reason_codes)
    triage_id = f"p2cti:triage:{canonical_sha256({'subject': seed_or_theory_ref, 'design_disposition': design_disposition, 'disposition': disposition, 'reason_codes': reasons})}"
    payload = {
        "triage_id": triage_id,
        "seed_or_theory_ref": seed_or_theory_ref,
        "design_disposition": design_disposition,
        "disposition": disposition,
        "reason_codes": reasons,
        "required_action": mapping.get("required_action"),
        "semantic_equivalence": mapping.get("semantic_equivalence"),
        "write_activation": False,
        "scientific_effect": "NONE",
        "candidate_effect": "NONE",
    }
    return _record(object_type="INTAKE_TRIAGE", source_frontier_id=source_frontier_id, identity={"triage_id": triage_id}, payload=payload)

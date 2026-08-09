"""Versioned stable causal comparison signatures for C2E v0.2 repair.

Operator authority: C2E2-G6-SIGNATURE-CONTRACT-SUPERSESSION SUPERSEDE.
This module is inactive candidate machinery only. It projects already-lawful
first-valid structural facts and selected-parent/dependency content into
comparison signatures. Wrapper record ids, local observation identity and
as-of chronology are deliberately outside the comparison basis.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping, Sequence

STRUCTURAL_AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION")
STRUCTURAL_COMPONENT_KEYS = {"status", "reason_codes", "facts", "source_object_ids"}
PARENT_KEYS = {"selected_parent_observation_ids", "selected_parent_object_ids", "dependency_states"}
DEPENDENCY_KEYS = {"dependency_id", "role", "status", "reason_codes"}
PROHIBITED_KEYS = {
    "record_id", "profile_output_id", "link_id", "bundle_id", "observation_id",
    "local_observation_id", "as_of_time", "first_valid_time", "evaluation_cutoff",
    "future", "outcome", "probability", "risk", "exposure", "trade", "trading",
    "execution", "family", "family_id", "medoid", "distance", "semantic_label",
    "selected_object_id", "fallback_object_id", "best_object", "nearest_object",
}


class StableSignatureError(ValueError):
    pass


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise StableSignatureError(marker)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StableSignatureError("NONCANONICAL_COMPARISON_CONTENT") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _scan(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in PROHIBITED_KEYS or lowered.endswith("_record_id") or lowered.endswith("_record_ids"):
                raise StableSignatureError(f"WRAPPER_OR_PROHIBITED_COMPARISON_FIELD:{path}.{key}")
            _scan(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan(item, f"{path}[{index}]")


def _strings(value: Any, marker: str) -> list[str]:
    _require(isinstance(value, list), marker)
    result = [str(item) for item in value]
    _require(len(result) == len(set(result)), f"DUPLICATE:{marker}")
    return sorted(result)


def _normalize_component(axis: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(raw) - STRUCTURAL_COMPONENT_KEYS)
    _require(not unknown, f"UNKNOWN_STRUCTURAL_COMPARISON_FIELD:{axis}:{','.join(unknown)}")
    _require("status" in raw, f"STRUCTURAL_COMPARISON_STATUS_REQUIRED:{axis}")
    _require("facts" in raw, f"STRUCTURAL_COMPARISON_FACTS_REQUIRED:{axis}")
    reasons = raw.get("reason_codes", [])
    _require(isinstance(reasons, list), f"STRUCTURAL_COMPARISON_REASONS_LIST:{axis}")
    source_object_ids = raw.get("source_object_ids", [])
    component = {
        "axis": axis,
        "status": str(raw["status"]),
        "reason_codes": sorted({str(item) for item in reasons}),
        "source_object_ids": _strings(source_object_ids, f"source_object_ids:{axis}"),
        "facts": copy.deepcopy(raw["facts"]),
    }
    _scan(component)
    return component


def normalize_structural_basis(raw: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(raw, Mapping), "STRUCTURAL_COMPARISON_BASIS_REQUIRED")
    unknown = sorted(set(raw) - set(STRUCTURAL_AXES))
    missing = sorted(set(STRUCTURAL_AXES) - set(raw))
    _require(not unknown, f"UNKNOWN_STRUCTURAL_COMPARISON_AXIS:{','.join(unknown)}")
    _require(not missing, f"MISSING_STRUCTURAL_COMPARISON_AXIS:{','.join(missing)}")
    basis = {axis: _normalize_component(axis, dict(raw[axis])) for axis in STRUCTURAL_AXES}
    _scan(basis)
    return basis


def normalize_parent_basis(raw: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(raw, Mapping), "PARENT_COMPARISON_BASIS_REQUIRED")
    unknown = sorted(set(raw) - PARENT_KEYS)
    _require(not unknown, f"UNKNOWN_PARENT_COMPARISON_FIELD:{','.join(unknown)}")
    dependencies_raw = raw.get("dependency_states", [])
    _require(isinstance(dependencies_raw, list), "PARENT_DEPENDENCY_STATES_LIST_REQUIRED")
    dependencies: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in dependencies_raw:
        _require(isinstance(item, Mapping), "PARENT_DEPENDENCY_STATE_OBJECT_REQUIRED")
        unknown_dep = sorted(set(item) - DEPENDENCY_KEYS)
        _require(not unknown_dep, f"UNKNOWN_PARENT_DEPENDENCY_FIELD:{','.join(unknown_dep)}")
        dependency_id = str(item.get("dependency_id", ""))
        _require(bool(dependency_id), "PARENT_DEPENDENCY_ID_REQUIRED")
        _require(dependency_id not in seen, "DUPLICATE_PARENT_DEPENDENCY_ID")
        seen.add(dependency_id)
        reasons = item.get("reason_codes", [])
        _require(isinstance(reasons, list), "PARENT_DEPENDENCY_REASONS_LIST_REQUIRED")
        dependencies.append({
            "dependency_id": dependency_id,
            "role": str(item.get("role", "UNSPECIFIED")),
            "status": str(item.get("status", "NOT_AVAILABLE")),
            "reason_codes": sorted({str(reason) for reason in reasons}),
        })
    dependencies.sort(key=lambda item: item["dependency_id"])
    basis = {
        "selected_parent_observation_ids": _strings(
            raw.get("selected_parent_observation_ids", []), "selected_parent_observation_ids"
        ),
        "selected_parent_object_ids": _strings(
            raw.get("selected_parent_object_ids", []), "selected_parent_object_ids"
        ),
        "dependency_states": dependencies,
    }
    _scan(basis)
    return basis


def build_comparison_signatures(comparison_source: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(comparison_source, Mapping), "COMPARISON_SOURCE_REQUIRED")
    unknown = sorted(set(comparison_source) - {"structural", "parent"})
    _require(not unknown, f"UNKNOWN_COMPARISON_SOURCE_FIELD:{','.join(unknown)}")
    _require("structural" in comparison_source, "STRUCTURAL_COMPARISON_SOURCE_REQUIRED")
    _require("parent" in comparison_source, "PARENT_COMPARISON_SOURCE_REQUIRED")
    structural_basis = normalize_structural_basis(dict(comparison_source["structural"]))
    parent_basis = normalize_parent_basis(dict(comparison_source["parent"]))
    return {
        "schema": "c2e_stable_comparison_signatures/v1",
        "signature_contract_id": "C2E.STABLE.COMPARISON.SIGNATURES.v1",
        "structural_basis": structural_basis,
        "parent_basis": parent_basis,
        "structural_signature_sha256": _digest(structural_basis),
        "parent_signature_sha256": _digest(parent_basis),
        "wrapper_identity_in_comparison": False,
        "active": False,
        "canonical": False,
        "authority": "CANDIDATE_INACTIVE_NONCANONICAL",
    }


def verify_comparison_signatures(value: Mapping[str, Any]) -> None:
    _require(value.get("signature_contract_id") == "C2E.STABLE.COMPARISON.SIGNATURES.v1", "SIGNATURE_CONTRACT_ID")
    rebuilt = build_comparison_signatures({
        "structural": value.get("structural_basis", {}),
        "parent": value.get("parent_basis", {}),
    })
    _require(value.get("structural_signature_sha256") == rebuilt["structural_signature_sha256"], "STRUCTURAL_SIGNATURE_MISMATCH")
    _require(value.get("parent_signature_sha256") == rebuilt["parent_signature_sha256"], "PARENT_SIGNATURE_MISMATCH")

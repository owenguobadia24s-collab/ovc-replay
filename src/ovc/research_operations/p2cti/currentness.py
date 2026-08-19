from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import re
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .identity import logical_id, source_frontier_id


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FRONTIER_ID = re.compile(r"^p2cti:frontier:[0-9a-f]{64}$")
_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p2cti/P2CTI_OWNER_SOURCE_REGISTRY_v0_1.json"
)
_BINDING_FIELDS = frozenset(
    {
        "owner_programme",
        "source_ref",
        "source_sha256",
        "semantic_generation",
        "authority_refs",
        "required",
    }
)
_FRONTIER_FIELDS = frozenset(
    {
        "schema_family",
        "schema_version",
        "object_type",
        "frontier_contract_id",
        "frontier_id",
        "required_owner_programmes",
        "source_bindings",
        "missing_required_owners",
        "conflicting_owner_programmes",
        "unresolved_reasons",
        "completeness_state",
        "authority_effect",
        "content_sha256",
    }
)


class FrontierValidationError(ValueError):
    """A closed-schema source frontier could not be validated."""


def _exact_string(value: Any, name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _exact_string_list(value: Any, name: str, *, allow_empty: bool = True) -> list[str]:
    if type(value) is not list:
        raise ValueError(f"{name} must be an array")
    if not allow_empty and not value:
        raise ValueError(f"{name} must be non-empty")
    if any(type(item) is not str or not item for item in value):
        raise ValueError(f"{name} values must be non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} values must be unique")
    return list(value)


def _load_frontier_contract() -> dict[str, Any]:
    registry = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    if registry.get("schema") != "ovc-p2cti-owner-source-registry/v0.1":
        raise RuntimeError("P2CTI owner/source registry schema mismatch")
    if registry.get("registry_id") != "P2CTI_OWNER_SOURCE_REGISTRY_v0_1":
        raise RuntimeError("P2CTI owner/source registry identity mismatch")
    rows = registry.get("owners")
    contract = registry.get("source_frontier_contract")
    if type(rows) is not list or not rows or not isinstance(contract, Mapping):
        raise RuntimeError("P2CTI owner/source registry frontier contract is incomplete")
    allowed = sorted(
        {
            row.get("owner")
            for row in rows
            if isinstance(row, Mapping)
            and type(row.get("owner")) is str
            and row.get("owner") != "DECLARED_AUTHORITY_OWNER"
        }
    )
    expected_fields = {
        "contract_id",
        "required_owner_programmes",
        "optional_owner_programmes",
        "missing_required_owner",
        "conflicting_owner_evidence",
        "historical_fallback",
    }
    if set(contract) != expected_fields:
        raise RuntimeError("P2CTI source-frontier contract must use the exact closed field set")
    contract_id = contract.get("contract_id")
    required = contract.get("required_owner_programmes")
    optional = contract.get("optional_owner_programmes")
    if type(contract_id) is not str or not contract_id:
        raise RuntimeError("P2CTI source-frontier contract_id is invalid")
    if type(required) is not list or type(optional) is not list:
        raise RuntimeError("P2CTI source-frontier owner sets must be arrays")
    if any(type(owner) is not str or not owner for owner in required + optional):
        raise RuntimeError("P2CTI source-frontier owner identifiers are invalid")
    if not required or len(required) != len(set(required)) or len(optional) != len(set(optional)):
        raise RuntimeError("P2CTI source-frontier owner sets must be unique and required non-empty")
    if set(required).intersection(optional) or sorted(required + optional) != allowed:
        raise RuntimeError("P2CTI source-frontier owner sets do not bind the owner registry")
    if contract.get("missing_required_owner") != "UNRESOLVED":
        raise RuntimeError("P2CTI missing required owner policy must be UNRESOLVED")
    if contract.get("conflicting_owner_evidence") != "CONFLICT":
        raise RuntimeError("P2CTI conflicting owner policy must be CONFLICT")
    if contract.get("historical_fallback") != "FORBIDDEN":
        raise RuntimeError("P2CTI historical fallback must be FORBIDDEN")
    return {
        "contract_id": contract_id,
        "required": tuple(sorted(required)),
        "optional": tuple(sorted(optional)),
        "allowed": frozenset(allowed),
    }


_FRONTIER_CONTRACT = _load_frontier_contract()
REQUIRED_CURRENTNESS_OWNERS = _FRONTIER_CONTRACT["required"]
OPTIONAL_CURRENTNESS_OWNERS = _FRONTIER_CONTRACT["optional"]


def _binding(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != _BINDING_FIELDS:
        raise ValueError("source binding must use the exact closed field set")
    owner = _exact_string(raw["owner_programme"], "owner_programme")
    source_ref = _exact_string(raw["source_ref"], "source_ref")
    digest = _exact_string(raw["source_sha256"], "source_sha256")
    generation = _exact_string(raw["semantic_generation"], "semantic_generation")
    if not _SHA256.fullmatch(digest):
        raise ValueError("source_sha256 must be lowercase SHA-256")
    refs = _exact_string_list(raw["authority_refs"], "authority_refs")
    if type(raw["required"]) is not bool:
        raise ValueError("required must be boolean")
    return {
        "authority_refs": sorted(refs),
        "owner_programme": owner,
        "required": raw["required"],
        "semantic_generation": generation,
        "source_ref": source_ref,
        "source_sha256": digest,
    }


def _binding_key(binding: Mapping[str, Any]) -> str:
    return f"{binding['owner_programme']}|{binding['source_ref']}"


def _frontier_completeness(
    bindings: Sequence[Mapping[str, Any]], explicit_reasons: Sequence[str]
) -> tuple[list[str], list[str], list[str], str]:
    owners = [binding["owner_programme"] for binding in bindings]
    unknown = sorted(set(owners) - _FRONTIER_CONTRACT["allowed"])
    if unknown:
        raise ValueError(f"source frontier contains unknown owner_programme: {unknown}")
    for binding in bindings:
        expected_required = binding["owner_programme"] in REQUIRED_CURRENTNESS_OWNERS
        if binding["required"] is not expected_required:
            raise ValueError(
                f"source binding required flag conflicts with registry for {binding['owner_programme']}"
            )
    counts = Counter(owners)
    conflicts = sorted(owner for owner, count in counts.items() if count > 1)
    missing = sorted(set(REQUIRED_CURRENTNESS_OWNERS) - set(owners))
    reasons = sorted(set(explicit_reasons))
    reasons.extend(f"OWNER_SOURCE_MISSING:{owner}" for owner in missing)
    reasons.extend(f"STATE_OWNER_CONFLICT:{owner}" for owner in conflicts)
    reasons = sorted(set(reasons))
    if conflicts:
        state = "INCOMPLETE_BLOCKING"
    elif missing or reasons:
        state = "UNRESOLVED"
    else:
        state = "COMPLETE"
    return missing, conflicts, reasons, state


def build_source_frontier(
    source_bindings: Sequence[Mapping[str, Any]],
    *,
    unresolved_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    if not isinstance(source_bindings, Sequence) or isinstance(source_bindings, (str, bytes)):
        raise ValueError("source_bindings must be a sequence")
    if not source_bindings:
        raise ValueError("at least one exact source binding is required")
    if not isinstance(unresolved_reasons, Sequence) or isinstance(unresolved_reasons, (str, bytes)):
        raise ValueError("unresolved_reasons must be a sequence")
    if any(type(reason) is not str or not reason for reason in unresolved_reasons):
        raise ValueError("unresolved_reasons values must be non-empty strings")
    normalized = [_binding(item) for item in source_bindings]
    normalized.sort(
        key=lambda item: (
            _binding_key(item),
            item["semantic_generation"],
            item["source_sha256"],
            tuple(item["authority_refs"]),
        )
    )
    binding_keys = [_binding_key(item) for item in normalized]
    if len(binding_keys) != len(set(binding_keys)):
        raise ValueError("source frontier contains duplicate owner/source bindings")
    missing, conflicts, reasons, state = _frontier_completeness(normalized, unresolved_reasons)
    frontier = source_frontier_id(normalized)
    body = {
        "schema_family": "P2CTI_SOURCE_FRONTIER",
        "schema_version": "0.1",
        "object_type": "P2CTI_SOURCE_FRONTIER_MANIFEST",
        "frontier_contract_id": _FRONTIER_CONTRACT["contract_id"],
        "frontier_id": frontier,
        "required_owner_programmes": list(REQUIRED_CURRENTNESS_OWNERS),
        "source_bindings": normalized,
        "missing_required_owners": missing,
        "conflicting_owner_programmes": conflicts,
        "unresolved_reasons": reasons,
        "completeness_state": state,
        "authority_effect": "NONE",
    }
    return {**body, "content_sha256": canonical_sha256(body)}


def _validated_frontier(frontier: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    try:
        if not isinstance(frontier, Mapping) or set(frontier) != _FRONTIER_FIELDS:
            raise ValueError("source frontier must use the exact closed field set")
        if frontier["schema_family"] != "P2CTI_SOURCE_FRONTIER":
            raise ValueError("source frontier schema_family is invalid")
        if frontier["schema_version"] != "0.1":
            raise ValueError("source frontier schema_version is invalid")
        if frontier["object_type"] != "P2CTI_SOURCE_FRONTIER_MANIFEST":
            raise ValueError("source frontier object_type is invalid")
        if frontier["frontier_contract_id"] != _FRONTIER_CONTRACT["contract_id"]:
            raise ValueError("source frontier contract identity is invalid")
        if frontier["authority_effect"] != "NONE":
            raise ValueError("source frontier authority_effect is invalid")
        frontier_id = _exact_string(frontier["frontier_id"], "frontier_id")
        content_sha256 = _exact_string(frontier["content_sha256"], "content_sha256")
        if not _FRONTIER_ID.fullmatch(frontier_id):
            raise ValueError("source frontier_id is invalid")
        if not _SHA256.fullmatch(content_sha256):
            raise ValueError("source frontier content_sha256 is invalid")
        required = _exact_string_list(
            frontier["required_owner_programmes"], "required_owner_programmes", allow_empty=False
        )
        missing = _exact_string_list(frontier["missing_required_owners"], "missing_required_owners")
        conflicts = _exact_string_list(
            frontier["conflicting_owner_programmes"], "conflicting_owner_programmes"
        )
        reasons = _exact_string_list(frontier["unresolved_reasons"], "unresolved_reasons")
        if required != list(REQUIRED_CURRENTNESS_OWNERS):
            raise ValueError("source frontier required owner set is not exact")
        raw_bindings = frontier["source_bindings"]
        if type(raw_bindings) is not list or not raw_bindings:
            raise ValueError("source_bindings must be a non-empty array")
        bindings = tuple(_binding(item) for item in raw_bindings)
        binding_keys = [_binding_key(item) for item in bindings]
        if len(binding_keys) != len(set(binding_keys)):
            raise ValueError("source frontier contains duplicate owner/source bindings")
        expected_missing, expected_conflicts, expected_reasons, expected_state = _frontier_completeness(
            bindings,
            [
                reason
                for reason in reasons
                if not reason.startswith("OWNER_SOURCE_MISSING:")
                and not reason.startswith("STATE_OWNER_CONFLICT:")
            ],
        )
        if (
            missing != expected_missing
            or conflicts != expected_conflicts
            or reasons != expected_reasons
            or frontier["completeness_state"] != expected_state
        ):
            raise ValueError("source frontier completeness does not bind the declared owner set")
        normalized = tuple(
            sorted(
                bindings,
                key=lambda item: (
                    _binding_key(item),
                    item["semantic_generation"],
                    item["source_sha256"],
                    tuple(item["authority_refs"]),
                ),
            )
        )
        if source_frontier_id(normalized) != frontier_id:
            raise ValueError("source frontier identity does not bind source_bindings")
        body = {name: frontier[name] for name in frontier if name != "content_sha256"}
        if canonical_sha256(body) != content_sha256:
            raise ValueError("source frontier content hash mismatch")
        return normalized
    except (KeyError, TypeError, ValueError) as exc:
        raise FrontierValidationError(str(exc)) from exc


def _safe_frontier_id(frontier: Any) -> str | None:
    if not isinstance(frontier, Mapping):
        return None
    value = frontier.get("frontier_id")
    return value if type(value) is str and _FRONTIER_ID.fullmatch(value) else None


def _invalid_frontier_evaluation(
    *,
    generation_id: str,
    prebuild_frontier: Any,
    prepublish_frontier: Any,
    errors: Sequence[str],
) -> dict[str, Any]:
    return {
        "schema": "ovc-p2cti-currentness-evaluation/v0.1",
        "generation_id": generation_id,
        "prebuild_source_frontier_id": _safe_frontier_id(prebuild_frontier),
        "source_frontier_id": _safe_frontier_id(prepublish_frontier),
        "currentness_state": "UNRESOLVED",
        "visibility_state": "REFERENCE_ONLY",
        "completeness_state": "UNRESOLVED",
        "frontier_validation_state": "INVALID",
        "warnings": ["CURRENTNESS_UNRESOLVED"],
        "validation_errors": list(errors),
        "frontiers_equal": False,
        "historical_generation_disposition": "RETAINED_ADDRESSABLE",
        "historical_fallback": "FORBIDDEN",
        "decision_bearing": False,
        "review_gate": "P2CTII-G2-ALG",
        "operational_pointer_switched": False,
        "authority_effect": "NONE",
        "advisory_pointer": None,
    }


def evaluate_two_point_currentness(
    *,
    series_id: str,
    generation_id: str,
    prebuild_frontier: Mapping[str, Any],
    prepublish_frontier: Mapping[str, Any],
) -> dict[str, Any]:
    """Return an advisory two-point evaluation; never switch an operational pointer."""

    errors: list[str] = []
    try:
        before = _validated_frontier(prebuild_frontier)
    except FrontierValidationError as exc:
        before = ()
        errors.append(f"PREBUILD:{exc}")
    try:
        after = _validated_frontier(prepublish_frontier)
    except FrontierValidationError as exc:
        after = ()
        errors.append(f"PREPUBLISH:{exc}")
    if errors:
        return _invalid_frontier_evaluation(
            generation_id=generation_id,
            prebuild_frontier=prebuild_frontier,
            prepublish_frontier=prepublish_frontier,
            errors=errors,
        )

    before_map = {_binding_key(item): item for item in before}
    after_map = {_binding_key(item): item for item in after}
    complete = (
        prebuild_frontier["completeness_state"] == "COMPLETE"
        and prepublish_frontier["completeness_state"] == "COMPLETE"
    )
    warnings: list[str]
    if not complete:
        currentness = "UNRESOLVED"
        warnings = ["CURRENTNESS_UNRESOLVED"]
    elif before_map == after_map:
        currentness = "CURRENT"
        warnings = []
    elif set(before_map) == set(after_map) and all(
        {name: before_map[key][name] for name in _BINDING_FIELDS if name != "authority_refs"}
        == {name: after_map[key][name] for name in _BINDING_FIELDS if name != "authority_refs"}
        for key in before_map
    ):
        currentness = "AUTHORITY_FRONTIER_CHANGED"
        warnings = ["AUTHORITY_FRONTIER_CHANGED"]
    elif set(before_map) == set(after_map) and any(
        before_map[key]["semantic_generation"] != after_map[key]["semantic_generation"]
        or before_map[key]["source_sha256"] != after_map[key]["source_sha256"]
        for key in before_map
    ):
        currentness = "SOURCE_GENERATION_ADVANCED"
        warnings = ["SOURCE_GENERATION_ADVANCED"]
    else:
        currentness = "REASSESSMENT_REQUIRED"
        warnings = ["CURRENTNESS_UNRESOLVED"]

    post_frontier_id = prepublish_frontier["frontier_id"]
    pointer_identity = {
        "series_id": series_id,
        "generation_id": generation_id,
        "source_frontier_id": post_frontier_id,
        "review_gate": "P2CTII-G2-ALG",
    }
    pointer_body = {
        "schema_family": "P2CTI_CURRENT_POINTER",
        "schema_version": "0.1",
        "pointer_id": logical_id("pointer", pointer_identity),
        "series_id": series_id,
        "generation_id": generation_id,
        "source_frontier_id": post_frontier_id,
        "currentness_state": currentness,
        "completeness_state": "COMPLETE" if complete else "UNRESOLVED",
        "decision_bearing": False,
        "review_gate": "P2CTII-G2-ALG",
        "authority_effect": "NONE",
    }
    pointer = {**pointer_body, "content_sha256": canonical_sha256(pointer_body)}
    return {
        "schema": "ovc-p2cti-currentness-evaluation/v0.1",
        "generation_id": generation_id,
        "prebuild_source_frontier_id": prebuild_frontier["frontier_id"],
        "source_frontier_id": post_frontier_id,
        "currentness_state": currentness,
        "visibility_state": "REFERENCE_ONLY",
        "completeness_state": pointer["completeness_state"],
        "warnings": warnings,
        "frontiers_equal": before_map == after_map,
        "historical_generation_disposition": "RETAINED_ADDRESSABLE",
        "historical_fallback": "FORBIDDEN",
        "decision_bearing": False,
        "review_gate": "P2CTII-G2-ALG",
        "operational_pointer_switched": False,
        "authority_effect": "NONE",
        "advisory_pointer": pointer,
    }


def dependency_bounded_invalidation(
    *,
    previous_frontier: Mapping[str, Any],
    current_frontier: Mapping[str, Any],
    generation_dependencies: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    previous = {_binding_key(item): item for item in _validated_frontier(previous_frontier)}
    current = {_binding_key(item): item for item in _validated_frontier(current_frontier)}
    changed = sorted(key for key in set(previous) | set(current) if previous.get(key) != current.get(key))
    affected = sorted(
        generation_id
        for generation_id, dependencies in generation_dependencies.items()
        if set(str(value) for value in dependencies).intersection(changed)
    )
    return {
        "changed_source_keys": changed,
        "affected_generation_ids": affected,
        "unaffected_generation_ids": sorted(set(generation_dependencies) - set(affected)),
        "historical_generations_preserved": True,
        "invalidation_scope": "EXACT_DEPENDENCIES_ONLY",
        "authority_effect": "NONE",
    }


def require_g2_alg_for_decision_bearing_pointer(*, g2_alg_status: str) -> None:
    if g2_alg_status != "PASS":
        raise PermissionError(
            "P2CTII-G2-ALG independent PASS is required before a decision-bearing current pointer"
        )

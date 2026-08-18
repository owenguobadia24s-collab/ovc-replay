from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .identity import logical_id, source_frontier_id


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


def _binding(raw: Mapping[str, Any]) -> dict[str, Any]:
    if set(raw) != _BINDING_FIELDS:
        raise ValueError("source binding must use the exact closed field set")
    digest = str(raw["source_sha256"])
    if len(digest) != 64 or digest.lower() != digest:
        raise ValueError("source_sha256 must be lowercase SHA-256")
    try:
        int(digest, 16)
    except ValueError as exc:
        raise ValueError("source_sha256 must be lowercase SHA-256") from exc
    refs = raw["authority_refs"]
    if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes)):
        raise ValueError("authority_refs must be a sequence")
    normalized_refs = sorted(str(value) for value in refs)
    if len(normalized_refs) != len(set(normalized_refs)):
        raise ValueError("authority_refs must be unique")
    if type(raw["required"]) is not bool:
        raise ValueError("required must be boolean")
    result = {name: raw[name] for name in sorted(_BINDING_FIELDS)}
    result["authority_refs"] = normalized_refs
    for name in ("owner_programme", "source_ref", "semantic_generation"):
        if not str(result[name]):
            raise ValueError(f"{name} must be non-empty")
    return result


def _binding_key(binding: Mapping[str, Any]) -> str:
    return f"{binding['owner_programme']}|{binding['source_ref']}"


def build_source_frontier(
    source_bindings: Sequence[Mapping[str, Any]],
    *,
    unresolved_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    if not source_bindings:
        raise ValueError("at least one exact source binding is required")
    normalized = [_binding(item) for item in source_bindings]
    normalized.sort(key=lambda item: (_binding_key(item), str(item["semantic_generation"]), str(item["source_sha256"])))
    keys = [_binding_key(item) for item in normalized]
    if len(keys) != len(set(keys)):
        raise ValueError("source frontier contains duplicate owner/source bindings")
    reasons = sorted(set(str(value) for value in unresolved_reasons))
    frontier = source_frontier_id(normalized)
    body = {
        "schema_family": "P2CTI_SOURCE_FRONTIER",
        "schema_version": "0.1",
        "object_type": "P2CTI_SOURCE_FRONTIER_MANIFEST",
        "frontier_id": frontier,
        "source_bindings": normalized,
        "completeness_state": "COMPLETE" if not reasons else "UNRESOLVED",
        "authority_effect": "NONE",
    }
    return {**body, "content_sha256": canonical_sha256(body)}


def _validated_frontier(frontier: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    expected = {
        "schema_family", "schema_version", "object_type", "frontier_id",
        "source_bindings", "completeness_state", "authority_effect", "content_sha256",
    }
    if set(frontier) != expected:
        raise ValueError("source frontier must use the exact closed field set")
    bindings = tuple(_binding(item) for item in frontier["source_bindings"])
    if source_frontier_id(bindings) != frontier["frontier_id"]:
        raise ValueError("source frontier identity does not bind source_bindings")
    body = {name: frontier[name] for name in frontier if name != "content_sha256"}
    if canonical_sha256(body) != frontier["content_sha256"]:
        raise ValueError("source frontier content hash mismatch")
    if frontier["completeness_state"] not in {"COMPLETE", "INCOMPLETE_BLOCKING", "UNRESOLVED"}:
        raise ValueError("source frontier completeness_state is invalid")
    return bindings


def evaluate_two_point_currentness(
    *,
    series_id: str,
    generation_id: str,
    prebuild_frontier: Mapping[str, Any],
    prepublish_frontier: Mapping[str, Any],
) -> dict[str, Any]:
    """Return an advisory two-point evaluation; never switch an operational pointer."""

    before = _validated_frontier(prebuild_frontier)
    after = _validated_frontier(prepublish_frontier)
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

    post_frontier_id = str(prepublish_frontier["frontier_id"])
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
    changed = sorted(
        key
        for key in set(previous) | set(current)
        if previous.get(key) != current.get(key)
    )
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

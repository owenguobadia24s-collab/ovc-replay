from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Mapping, Sequence

from .canonical import canonical_sha256, logical_id


class AtlasArchitectureManifestError(ValueError):
    """Raised when an architecture manifest is incomplete or ambiguous."""


CURRENTNESS_STATES = {"CURRENT", "STALE_SOURCE_HASH", "SUPERSEDED_SOURCE", "UNRESOLVED"}
_HASH_LENGTHS = {"sha1": 40, "sha256": 64}


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise AtlasArchitectureManifestError(code)


def validate_architecture_manifest(manifest: Mapping[str, Any]) -> None:
    _require(manifest.get("schema") == "ovc-atlas-architecture-manifest/v1", "ATLAS_ARCHITECTURE_SCHEMA_INVALID")
    _require(bool(str(manifest.get("manifest_id", "")).strip()), "ATLAS_ARCHITECTURE_ID_REQUIRED")
    _require(manifest.get("authority_effect") == "NONE_SOURCE_BOUND_DESIGN_INDEX_ONLY", "ATLAS_ARCHITECTURE_AUTHORITY_INVALID")
    bindings = manifest.get("source_bindings")
    _require(isinstance(bindings, Sequence) and not isinstance(bindings, (str, bytes)) and bool(bindings), "ATLAS_ARCHITECTURE_SOURCES_REQUIRED")
    locators: set[str] = set()
    for binding in bindings:
        _require(isinstance(binding, Mapping), "ATLAS_ARCHITECTURE_SOURCE_INVALID")
        locator = str(binding.get("locator", ""))
        algorithm = str(binding.get("hash_algorithm", ""))
        digest = str(binding.get("expected_hash", ""))
        _require(bool(locator) and locator not in locators, "ATLAS_ARCHITECTURE_SOURCE_DUPLICATE")
        _require(algorithm in _HASH_LENGTHS, "ATLAS_ARCHITECTURE_HASH_ALGORITHM_INVALID")
        _require(re.fullmatch(f"[0-9a-f]{{{_HASH_LENGTHS[algorithm]}}}", digest) is not None, "ATLAS_ARCHITECTURE_HASH_INVALID")
        locators.add(locator)
    declarations = manifest.get("declarations")
    _require(isinstance(declarations, Sequence) and not isinstance(declarations, (str, bytes)), "ATLAS_ARCHITECTURE_DECLARATIONS_INVALID")
    for declaration in declarations:
        _require(isinstance(declaration, Mapping), "ATLAS_ARCHITECTURE_DECLARATION_INVALID")
        _require(set(declaration) >= {"subject", "predicate", "object", "scope_hints"}, "ATLAS_ARCHITECTURE_DECLARATION_INCOMPLETE")


def manifest_currentness_record(
    manifest: Mapping[str, Any],
    *,
    observed_source_hashes: Mapping[str, str],
    repository_commit: str,
    repository_tree: str,
    superseded_manifest_ids: Sequence[str] = (),
) -> dict[str, Any]:
    validate_architecture_manifest(manifest)
    comparisons = []
    for binding in manifest["source_bindings"]:
        locator = str(binding["locator"])
        actual = observed_source_hashes.get(locator)
        comparisons.append(
            {
                "locator": locator,
                "hash_algorithm": binding["hash_algorithm"],
                "expected_hash": binding["expected_hash"],
                "observed_hash": actual,
                "status": "UNRESOLVED" if actual is None else "MATCH" if actual == binding["expected_hash"] else "MISMATCH",
            }
        )
    manifest_id = str(manifest["manifest_id"])
    if manifest_id in set(superseded_manifest_ids):
        status = "SUPERSEDED_SOURCE"
    elif any(row["status"] == "UNRESOLVED" for row in comparisons):
        status = "UNRESOLVED"
    elif any(row["status"] == "MISMATCH" for row in comparisons):
        status = "STALE_SOURCE_HASH"
    else:
        status = "CURRENT"
    body = {
        "schema": "ovc-atlas-manifest-currentness-record/v1",
        "record_id": logical_id(
            "manifest-currentness",
            {
                "manifest_id": manifest_id,
                "repository_commit": repository_commit,
                "repository_tree": repository_tree,
                "comparisons": comparisons,
                "status": status,
            },
        ),
        "manifest_id": manifest_id,
        "repository_commit": repository_commit,
        "repository_tree": repository_tree,
        "status": status,
        "source_comparisons": comparisons,
        "current_declarative_eligibility": status == "CURRENT",
        "history_visibility": "PRESERVED",
        "canonical_promotion": "DENIED_PENDING_WP4_RESOLUTION",
        "authority_effect": "NONE_CURRENTNESS_OBSERVATION_ONLY",
    }
    return {**body, "record_hash": canonical_sha256(body)}


def architecture_manifest_observations(manifest: Mapping[str, Any], currentness: Mapping[str, Any]) -> dict[str, Any]:
    validate_architecture_manifest(manifest)
    _require(currentness.get("manifest_id") == manifest.get("manifest_id"), "ATLAS_ARCHITECTURE_CURRENTNESS_MISMATCH")
    _require(currentness.get("status") in CURRENTNESS_STATES, "ATLAS_ARCHITECTURE_CURRENTNESS_INVALID")
    declarations = []
    for declaration in manifest["declarations"]:
        body = {
            "manifest_id": manifest["manifest_id"],
            "subject": declaration["subject"],
            "predicate": declaration["predicate"],
            "object": deepcopy(declaration["object"]),
            "scope_hints": deepcopy(declaration["scope_hints"]),
            "manifest_currentness": currentness["status"],
        }
        declarations.append(
            {
                "observation_id": logical_id("architecture-observation", body),
                **body,
                "evidence_class": "SOURCE_EXPLICIT",
                "current_declarative_eligibility": currentness["status"] == "CURRENT",
                "canonical_promotion": "DENIED_PENDING_WP4_RESOLUTION",
                "authority_effect": "NONE_DESIGN_CANON_DECLARATION_ONLY",
            }
        )
    declarations.sort(key=lambda row: row["observation_id"])
    result = {
        "schema": "ovc-atlas-architecture-observation-set/v1",
        "manifest_id": manifest["manifest_id"],
        "manifest_currentness_record_id": currentness["record_id"],
        "declarations": declarations,
        "canonical_assertions": [],
        "authority_effect": "NONE_ARCHITECTURE_OBSERVATIONS_ONLY",
    }
    return {**result, "observation_set_hash": canonical_sha256(result)}

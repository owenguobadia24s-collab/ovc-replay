from __future__ import annotations

from typing import Any, Mapping

from ovc.development.identity import canonical_sha256


class ReleaseBuildError(ValueError):
    """Raised when a Skill release cannot receive a lawful immutable identity."""


_ALLOWED_CLASSES = {"NORMATIVE", "DESCRIPTIVE"}


def resolve_field_classification(fields: Mapping[str, Any], declared: Mapping[str, str] | None = None) -> dict[str, str]:
    declared = dict(declared or {})
    unknown = sorted(set(declared) - set(fields))
    if unknown:
        raise ReleaseBuildError(f"classification references unknown fields {unknown}")
    resolved: dict[str, str] = {}
    for key in sorted(fields):
        classification = declared.get(key, "NORMATIVE")
        if classification not in _ALLOWED_CLASSES:
            classification = "NORMATIVE"
        resolved[key] = classification
    return resolved


def build_skill_release_bundle(
    *,
    skill_id: str,
    logical_name: str,
    semantic_version: str,
    fields: Mapping[str, Any],
    field_classification: Mapping[str, str] | None,
    source_refs: tuple[str, ...] | list[str],
) -> dict[str, Any]:
    if not skill_id or not logical_name or not semantic_version or not source_refs:
        raise ReleaseBuildError("skill_id, logical_name, semantic_version and source_refs are required")
    resolved = resolve_field_classification(fields, field_classification)
    normative = {key: fields[key] for key in sorted(fields) if resolved[key] == "NORMATIVE"}
    descriptive = {key: fields[key] for key in sorted(fields) if resolved[key] == "DESCRIPTIVE"}
    identity_payload = {
        "skill_id": skill_id,
        "logical_name": logical_name,
        "semantic_version": semantic_version,
        "normative_payload": normative,
    }
    digest = canonical_sha256(identity_payload, role="SKILL_RELEASE_NORMATIVE_BUNDLE")
    return {
        "schema": "ovc-dsai-skill-release-bundle/v1",
        "skill_id": skill_id,
        "logical_name": logical_name,
        "semantic_version": semantic_version,
        "release_id": f"{skill_id}@{semantic_version}+sha256:{digest}",
        "normative_bundle_hash": digest,
        "resolved_field_classification": resolved,
        "normative_payload": normative,
        "descriptive_payload": descriptive,
        "source_refs": sorted(str(ref) for ref in source_refs),
        "authority_effect": "NONE",
    }

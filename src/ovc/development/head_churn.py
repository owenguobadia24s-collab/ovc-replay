"""Deterministic classification of main-head movement for parallel OVC packets.

The classifier is deliberately path/identity conservative. It does not inspect market
content, grant authority, or decide whether a reserved gate may be bypassed.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping


CLASSES = (
    "IRRELEVANT",
    "INTEGRATION_RELEVANT",
    "SEMANTIC_AUTHORITY_RELEVANT",
    "UNRESOLVED_REQUIRES_FOOTPRINT",
)

_ACTIONS = {
    "IRRELEVANT": (
        "retain_bound_scientific_evidence_if_identities_unchanged",
        "run_required_exact_integration_assurance",
    ),
    "INTEGRATION_RELEVANT": (
        "reconcile_with_current_main",
        "rerun_impacted_and_required_exact_integration_assurance",
        "retain_bound_scientific_evidence_if_identities_unchanged",
    ),
    "SEMANTIC_AUTHORITY_RELEVANT": (
        "perform_full_semantic_repreflight",
        "reresolve_bindings_and_authority",
        "regenerate_dependent_evidence_when_required",
        "block_or_supersede_if_packet_premise_changed",
    ),
    "UNRESOLVED_REQUIRES_FOOTPRINT": (
        "materialize_dependency_footprint",
        "do_not_reuse_scientific_evidence_until_resolved",
    ),
}

_EVIDENCE_REUSE = {
    "IRRELEVANT": "PERMITTED_IF_BOUND_IDENTITIES_UNCHANGED",
    "INTEGRATION_RELEVANT": "PERMITTED_IF_BOUND_IDENTITIES_UNCHANGED",
    "SEMANTIC_AUTHORITY_RELEVANT": "PROHIBITED_PENDING_SEMANTIC_REPREFLIGHT",
    "UNRESOLVED_REQUIRES_FOOTPRINT": "PROHIBITED_PENDING_FOOTPRINT",
}


@dataclass(frozen=True)
class MatchEvidence:
    path: str
    rule: str
    pattern: str
    classification: str

    def as_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "rule": self.rule,
            "pattern": self.pattern,
            "classification": self.classification,
        }


def _normalise_path(path: str) -> str:
    value = path.replace("\\", "/").strip()
    while value.startswith("./"):
        value = value[2:]
    if not value or value.startswith("/"):
        raise ValueError(f"invalid repository-relative path: {path!r}")
    if ".." in PurePosixPath(value).parts:
        raise ValueError(f"path traversal is not allowed: {path!r}")
    return value


def _normalise_patterns(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({_normalise_path(value) for value in values}))


def _matches(path: str, pattern: str) -> bool:
    # fnmatchcase handles ** as a broad wildcard over '/' which is sufficient for
    # repository policy patterns and keeps the result platform-independent.
    return fnmatchcase(path, pattern)


def _validate_sha(value: str, label: str) -> str:
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"{label} must be a lowercase 40-character git SHA")
    return value


def _validate_footprint(footprint: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema",
        "programme_id",
        "packet_id",
        "plan_id",
        "baseline_main_sha",
        "dependency_paths",
        "semantic_authority_paths",
        "shared_integration_paths",
        "candidate_owned_paths",
        "identity_bindings",
        "external_identity_bindings",
    }
    missing = required - set(footprint)
    if missing:
        raise ValueError(f"dependency footprint missing fields: {sorted(missing)}")
    if footprint["schema"] != "ovc-parallel-development-dependency-footprint/v1":
        raise ValueError("unsupported dependency footprint schema")
    baseline = _validate_sha(str(footprint["baseline_main_sha"]), "baseline_main_sha")
    identity_bindings = []
    for item in footprint["identity_bindings"]:
        if set(item) != {"path", "identity"}:
            raise ValueError("identity binding must contain only path and identity")
        identity_bindings.append(
            {"path": _normalise_path(str(item["path"])), "identity": str(item["identity"])}
        )
    external_bindings = []
    for item in footprint["external_identity_bindings"]:
        if set(item) != {"logical_name", "identity"}:
            raise ValueError("external identity binding must contain logical_name and identity")
        external_bindings.append(
            {"logical_name": str(item["logical_name"]), "identity": str(item["identity"])}
        )
    return {
        "schema": footprint["schema"],
        "programme_id": str(footprint["programme_id"]),
        "packet_id": str(footprint["packet_id"]),
        "plan_id": str(footprint["plan_id"]),
        "baseline_main_sha": baseline,
        "dependency_paths": _normalise_patterns(footprint["dependency_paths"]),
        "semantic_authority_paths": _normalise_patterns(footprint["semantic_authority_paths"]),
        "shared_integration_paths": _normalise_patterns(footprint["shared_integration_paths"]),
        "candidate_owned_paths": _normalise_patterns(footprint["candidate_owned_paths"]),
        "identity_bindings": tuple(sorted(identity_bindings, key=lambda row: (row["path"], row["identity"]))),
        "external_identity_bindings": tuple(
            sorted(external_bindings, key=lambda row: (row["logical_name"], row["identity"]))
        ),
    }


def _global_integration_patterns(policy: Mapping[str, Any] | None) -> tuple[str, ...]:
    if policy is None:
        return ()
    patterns = policy.get("global_integration_patterns", ())
    if not isinstance(patterns, (list, tuple)):
        raise ValueError("policy global_integration_patterns must be an array")
    return _normalise_patterns(patterns)


def classify_main_head_movement(
    *,
    baseline_main_sha: str,
    current_main_sha: str,
    changed_main_paths: Iterable[str],
    footprint: Mapping[str, Any] | None,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify intervening main changes and emit a deterministic receipt."""

    baseline = _validate_sha(baseline_main_sha, "baseline_main_sha")
    current = _validate_sha(current_main_sha, "current_main_sha")
    changed = tuple(sorted({_normalise_path(path) for path in changed_main_paths}))

    matches: list[MatchEvidence] = []
    if baseline == current and changed:
        raise ValueError("changed paths supplied even though baseline and current main are identical")
    if baseline != current and not changed:
        # A merge can theoretically alter only metadata, but the classifier is path based and
        # must not infer irrelevance without file evidence.
        classification = "UNRESOLVED_REQUIRES_FOOTPRINT"
        validated_footprint = None if footprint is None else _validate_footprint(footprint)
    elif not changed:
        classification = "IRRELEVANT"
        validated_footprint = None if footprint is None else _validate_footprint(footprint)
    elif footprint is None:
        classification = "UNRESOLVED_REQUIRES_FOOTPRINT"
        validated_footprint = None
    else:
        validated_footprint = _validate_footprint(footprint)
        if validated_footprint["baseline_main_sha"] != baseline:
            raise ValueError("footprint baseline_main_sha does not match classifier baseline")

        semantic_patterns = tuple(
            sorted(
                set(validated_footprint["dependency_paths"])
                | set(validated_footprint["semantic_authority_paths"])
                | {row["path"] for row in validated_footprint["identity_bindings"]}
            )
        )
        integration_patterns = tuple(
            sorted(
                set(validated_footprint["shared_integration_paths"])
                | set(validated_footprint["candidate_owned_paths"])
                | set(_global_integration_patterns(policy))
            )
        )

        for path in changed:
            for pattern in semantic_patterns:
                if _matches(path, pattern):
                    matches.append(
                        MatchEvidence(path, "consumed_or_semantic_dependency_changed", pattern, "SEMANTIC_AUTHORITY_RELEVANT")
                    )
            for pattern in integration_patterns:
                if _matches(path, pattern):
                    matches.append(
                        MatchEvidence(path, "shared_or_candidate_integration_path_changed", pattern, "INTEGRATION_RELEVANT")
                    )

        if any(row.classification == "SEMANTIC_AUTHORITY_RELEVANT" for row in matches):
            classification = "SEMANTIC_AUTHORITY_RELEVANT"
        elif any(row.classification == "INTEGRATION_RELEVANT" for row in matches):
            classification = "INTEGRATION_RELEVANT"
        else:
            classification = "IRRELEVANT"

    payload: dict[str, Any] = {
        "schema": "ovc-parallel-development-head-movement-receipt/v1",
        "baseline_main_sha": baseline,
        "current_main_sha": current,
        "main_moved": baseline != current,
        "changed_main_paths": list(changed),
        "changed_main_path_count": len(changed),
        "classification": classification,
        "required_actions": list(_ACTIONS[classification]),
        "scientific_evidence_reuse": _EVIDENCE_REUSE[classification],
        "matches": [row.as_dict() for row in sorted(matches, key=lambda item: (item.path, item.classification, item.pattern))],
        "footprint_identity": None,
    }
    if validated_footprint is not None:
        footprint_payload = {
            "programme_id": validated_footprint["programme_id"],
            "packet_id": validated_footprint["packet_id"],
            "plan_id": validated_footprint["plan_id"],
            "baseline_main_sha": validated_footprint["baseline_main_sha"],
            "dependency_paths": list(validated_footprint["dependency_paths"]),
            "semantic_authority_paths": list(validated_footprint["semantic_authority_paths"]),
            "shared_integration_paths": list(validated_footprint["shared_integration_paths"]),
            "candidate_owned_paths": list(validated_footprint["candidate_owned_paths"]),
            "identity_bindings": list(validated_footprint["identity_bindings"]),
            "external_identity_bindings": list(validated_footprint["external_identity_bindings"]),
        }
        encoded = json.dumps(footprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        payload["footprint_identity"] = hashlib.sha256(encoded).hexdigest()

    receipt_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["receipt_sha256"] = hashlib.sha256(receipt_bytes).hexdigest()
    return payload

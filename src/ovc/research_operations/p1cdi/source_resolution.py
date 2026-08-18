from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import re
from typing import Any

from ovc.research_operations.canonical import canonical_sha256


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STATES = frozenset({"RESOLVED", "UNRESOLVED", "CONFLICT", "UNAVAILABLE"})
_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p1cdi/source_owner_registry.json"
)


def _load_source_policy() -> tuple[dict[str, tuple[str, str]], tuple[str, ...]]:
    registry = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    if registry.get("schema") != "p1cdi-source-owner-registry/v0.1":
        raise RuntimeError("P1CDI source-owner registry schema mismatch")
    if registry.get("status") != "CLOSED":
        raise RuntimeError("P1CDI source-owner registry must be CLOSED")
    rows = registry.get("entries")
    predicates = registry.get("currentness_required_predicates")
    if not isinstance(rows, list) or not isinstance(predicates, list):
        raise RuntimeError("P1CDI source-owner registry is incomplete")
    policy: dict[str, tuple[str, str]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {
            "predicate", "owner", "missing", "p1cdi_write"
        }:
            raise RuntimeError("P1CDI source-owner registry entry is invalid")
        predicate = row["predicate"]
        owner = row["owner"]
        missing = row["missing"]
        if not all(type(value) is str and value for value in (predicate, owner, missing)):
            raise RuntimeError("P1CDI source-owner registry values must be non-empty strings")
        if predicate in policy:
            raise RuntimeError(f"duplicate P1CDI owner predicate: {predicate}")
        policy[predicate] = (owner, missing)
    if any(type(predicate) is not str or predicate not in policy for predicate in predicates):
        raise RuntimeError("P1CDI currentness predicate is not registry-bound")
    if len(predicates) != len(set(predicates)):
        raise RuntimeError("P1CDI currentness predicates must be unique")
    required_owners = tuple(sorted(policy[predicate][0] for predicate in predicates))
    if len(required_owners) != len(set(required_owners)):
        raise RuntimeError("P1CDI currentness owners must be unique")
    return policy, required_owners


_SOURCE_POLICY, REQUIRED_CURRENTNESS_OWNERS = _load_source_policy()


def _normalized_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    required = {"predicate", "owner", "source_ref", "generation_ref", "source_sha256", "resolution_state"}
    if set(evidence) != required:
        raise ValueError("source evidence must use the exact closed field set")
    if evidence["resolution_state"] not in _STATES:
        raise ValueError(f"invalid resolution_state: {evidence['resolution_state']}")
    if not _SHA256.fullmatch(str(evidence["source_sha256"])):
        raise ValueError("source_sha256 must be lowercase SHA-256")
    return {name: evidence[name] for name in sorted(required)}


def resolve_owner_predicate(
    predicate: str, evidence: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Resolve one high-risk predicate without recency/path/title fallback."""

    if predicate not in _SOURCE_POLICY:
        raise ValueError(f"unknown owner predicate: {predicate}")
    expected_owner, missing_reason = _SOURCE_POLICY[predicate]
    rows = [_normalized_evidence(item) for item in evidence if item.get("predicate") == predicate]
    wrong_owner = [item for item in rows if item["owner"] != expected_owner]
    if wrong_owner:
        return _resolution(predicate, expected_owner, "CONFLICT", None, ["OWNER_SEMANTIC_CONFLICT"])
    if not rows:
        return _resolution(predicate, expected_owner, "UNRESOLVED", None, [missing_reason])
    if any(item["resolution_state"] == "CONFLICT" for item in rows):
        return _resolution(predicate, expected_owner, "CONFLICT", None, ["OWNER_SEMANTIC_CONFLICT"])
    resolved = [item for item in rows if item["resolution_state"] == "RESOLVED"]
    if not resolved:
        return _resolution(predicate, expected_owner, "UNRESOLVED", None, [missing_reason])
    identities = {
        (str(item["source_ref"]), str(item["generation_ref"]), str(item["source_sha256"]))
        for item in resolved
    }
    if len(identities) != 1 or len(resolved) != len(rows):
        return _resolution(predicate, expected_owner, "CONFLICT", None, ["OWNER_SEMANTIC_CONFLICT"])
    selected = sorted(resolved, key=lambda item: tuple(str(item[name]) for name in sorted(item)))[0]
    return _resolution(predicate, expected_owner, "RESOLVED", selected, [])


def _resolution(
    predicate: str,
    owner: str,
    state: str,
    source: Mapping[str, Any] | None,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "predicate": predicate,
        "controlling_owner": owner,
        "resolution_state": state,
        "resolved_source": dict(source) if source is not None else None,
        "reason_codes": reasons,
        "decision_bearing": False,
        "authority_effect": "NONE",
    }


def build_source_frontier(
    *, frontier_id: str, resolved_at: str, owner_entries: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if not frontier_id or not resolved_at or not owner_entries:
        raise ValueError("frontier_id, resolved_at, and owner_entries are required")
    normalized: list[dict[str, Any]] = []
    for raw in owner_entries:
        required = {"owner", "source_ref", "generation_ref", "source_sha256", "resolution_state"}
        if set(raw) != required:
            raise ValueError("source frontier entries must use the exact closed field set")
        if raw["resolution_state"] not in _STATES:
            raise ValueError(f"invalid resolution_state: {raw['resolution_state']}")
        if not _SHA256.fullmatch(str(raw["source_sha256"])):
            raise ValueError("source_sha256 must be lowercase SHA-256")
        normalized.append({key: raw[key] for key in sorted(required)})
    normalized.sort(
        key=lambda item: (
            str(item["owner"]),
            str(item["source_ref"]),
            str(item["generation_ref"]),
            str(item["source_sha256"]),
            str(item["resolution_state"]),
        )
    )
    owners = [str(item["owner"]) for item in normalized]
    duplicate_required_owners = sorted(
        owner for owner in REQUIRED_CURRENTNESS_OWNERS if owners.count(owner) > 1
    )
    missing_required_owners = sorted(set(REQUIRED_CURRENTNESS_OWNERS) - set(owners))
    states = {item["resolution_state"] for item in normalized}
    if duplicate_required_owners or "CONFLICT" in states:
        completeness_state = "CONFLICT"
        reason_codes = ["OWNER_SEMANTIC_CONFLICT"]
    elif missing_required_owners or states - {"RESOLVED"}:
        completeness_state = "UNRESOLVED"
        reason_codes = ["UNRESOLVED_CURRENTNESS"]
    else:
        completeness_state = "COMPLETE"
        reason_codes = []
    identity = {
        "required_owners": list(REQUIRED_CURRENTNESS_OWNERS),
        "owner_entries": normalized,
        "missing_required_owners": missing_required_owners,
        "duplicate_required_owners": duplicate_required_owners,
        "completeness_state": completeness_state,
        "reason_codes": reason_codes,
    }
    digest = canonical_sha256(identity)
    return {
        "record_type": "SourceFrontierManifest",
        "schema_version": "0.1",
        "frontier_id": frontier_id,
        "resolved_at": resolved_at,
        **identity,
        "frontier_sha256": digest,
        "authority_effect": "NONE",
    }

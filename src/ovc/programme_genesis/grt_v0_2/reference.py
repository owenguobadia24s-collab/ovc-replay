"""GRT2-WP3A deterministic non-enforcing reference runtime."""
from __future__ import annotations

import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ovc.programme_genesis._topology_engine import tracked_inventory

from .constitution import ARTIFACT_CLASSES, LIFECYCLE_CLASSES, RELATIONSHIP_TYPES
from .debt import B0_MEMBER_COUNT, B0_MEMBERSHIP_SHA256, baseline_membership_sha256, validate_baseline_members
from .serialization import SERIALIZATION_ID, canonical_sha256

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX40_OR_64 = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class ReferenceRuntimeError(ValueError):
    pass


def _path(value: str) -> str:
    if not isinstance(value, str):
        raise ReferenceRuntimeError("GRT_OBSERVED_PATH_INVALID")
    path = value.replace("\\", "/").strip("/")
    if not path or path.startswith("../") or "/../" in f"/{path}/" or path.startswith("./"):
        raise ReferenceRuntimeError("GRT_OBSERVED_PATH_INVALID")
    return path


def _artifact_type_from_path(path: str) -> str | None:
    p = path.lower()
    root = p.split("/", 1)[0]
    if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml")):
        return "WORKFLOW"
    root_types = {
        "src": "IMPLEMENTATION", "contracts": "CONTRACT", "schemas": "SCHEMA",
        "registries": "REGISTRY", "fixtures": "FIXTURE", "tests": "TEST",
        "scripts": "TOOLING", "tools": "TOOLING", "artifacts": "GENERATED_ARTIFACT",
    }
    if root in root_types:
        return root_types[root]
    if root == "docs":
        if "/decisions/" in f"/{p}" or p.endswith("decision.json"):
            return "DECISION_RECORD"
        if "/implementation-plans/" in f"/{p}" or "/plans/" in f"/{p}":
            return "PLAN"
        return "DOCUMENTATION"
    return None


def observe_component(*, tree_hash: str, path: str, content_hash: str, component_type: str = "file") -> dict[str, Any]:
    path = _path(path)
    if not _HEX40.fullmatch(tree_hash):
        raise ReferenceRuntimeError("GRT_OBSERVED_TREE_INVALID")
    if not _HEX40_OR_64.fullmatch(content_hash):
        raise ReferenceRuntimeError("GRT_OBSERVED_CONTENT_HASH_INVALID")
    if component_type not in {"file", "dir", "symlink", "submodule"}:
        raise ReferenceRuntimeError("GRT_OBSERVED_COMPONENT_TYPE_INVALID")
    identity = {"tree_identity": tree_hash, "path": path, "content_hash": content_hash, "component_type": component_type}
    return {
        "component_id": "GRT.OBS." + canonical_sha256(identity)[:24], **identity,
        "scanner_version": "GRT-REFERENCE-WP3A.v1", "observed_relationships": [],
    }


def classify_observation(observation: Mapping[str, Any], binding: Mapping[str, Any] | None = None) -> dict[str, Any]:
    binding = dict(binding or {})
    path = _path(str(observation.get("path", "")))
    artifact_type = binding.get("artifact_type", _artifact_type_from_path(path))
    if artifact_type is None:
        raise ReferenceRuntimeError("GRT_ARTIFACT_CLASS_NOT_EVALUABLE")
    if artifact_type not in ARTIFACT_CLASSES:
        raise ReferenceRuntimeError("GRT_ARTIFACT_CLASS_INVALID")
    explicit_id = binding.get("artifact_id")
    if explicit_id is not None and (not isinstance(explicit_id, str) or not explicit_id):
        raise ReferenceRuntimeError("GRT_ARTIFACT_ID_INVALID")
    candidate = {"artifact_type": artifact_type, "content_hash": observation["content_hash"], "logical_namespace": binding.get("logical_namespace")}
    artifact_id = explicit_id or "GRT.ARTIFACT.CANDIDATE." + canonical_sha256(candidate)[:24]
    lifecycle = binding.get("lifecycle_class")
    if lifecycle is None:
        lifecycle, lifecycle_source, status = "PROPOSED_UNADMITTED", "DEFAULT_NON_AUTHORITY", "PARTIAL"
    else:
        if lifecycle not in LIFECYCLE_CLASSES:
            raise ReferenceRuntimeError("GRT_ARTIFACT_LIFECYCLE_INVALID")
        lifecycle_source, status = "SOURCE_EXPLICIT", "RESOLVED"
    relationships = []
    for rel in binding.get("relationships", []):
        if not isinstance(rel, Mapping) or rel.get("relationship_type") not in RELATIONSHIP_TYPES:
            raise ReferenceRuntimeError("GRT_ARTIFACT_RELATIONSHIP_INVALID")
        if not rel.get("object_artifact_id"):
            raise ReferenceRuntimeError("GRT_ARTIFACT_RELATIONSHIP_TARGET_MISSING")
        relationships.append({
            "relationship_type": rel["relationship_type"], "object_artifact_id": rel["object_artifact_id"],
            "evidence_status": rel.get("evidence_status", "SOURCE_EXPLICIT"),
            "evidence_refs": sorted(set(rel.get("evidence_refs", []))), "authority_effect": rel.get("authority_effect", "NONE"),
        })
    relationships.sort(key=lambda item: (item["relationship_type"], item["object_artifact_id"]))
    return {
        "artifact_id": artifact_id, "artifact_type": artifact_type, "lifecycle_class": lifecycle,
        "lifecycle_source": lifecycle_source, "physical_components": [observation["component_id"]],
        "logical_namespace": binding.get("logical_namespace"), "programme_binding": binding.get("programme_binding"),
        "genesis_binding": binding.get("genesis_binding"), "declared_relationships": relationships,
        "evidence": [observation["component_id"]], "constitution_version": "v0.2", "artifact_status": status,
        "binding_status": "SOURCE_EXPLICIT" if binding else "CANDIDATE_RELATION",
    }


def build_reference_graph(*, tree_hash: str, components: Sequence[Mapping[str, Any]], bindings_by_path: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    if not _HEX40.fullmatch(tree_hash):
        raise ReferenceRuntimeError("GRT_REFERENCE_TREE_INVALID")
    bindings = {_path(k): v for k, v in (bindings_by_path or {}).items()}
    observations, grouped = [], defaultdict(list)
    for raw in sorted(components, key=lambda item: _path(str(item.get("path", "")))):
        obs = observe_component(tree_hash=tree_hash, path=str(raw.get("path", "")), content_hash=str(raw.get("content_hash", "")), component_type=str(raw.get("component_type", "file")))
        observations.append(obs)
        art = classify_observation(obs, bindings.get(obs["path"]))
        grouped[art["artifact_id"]].append(art)
    artifacts, unresolved = [], []
    for artifact_id in sorted(grouped):
        group, exemplar = grouped[artifact_id], grouped[artifact_id][0]
        keys = ("artifact_type", "lifecycle_class", "logical_namespace", "programme_binding", "genesis_binding")
        if any(item[key] != exemplar[key] for item in group[1:] for key in keys):
            raise ReferenceRuntimeError("GRT_ARTIFACT_IDENTITY_COLLISION")
        combined = dict(exemplar)
        combined["physical_components"] = sorted({x for item in group for x in item["physical_components"]})
        combined["evidence"] = sorted({x for item in group for x in item["evidence"]})
        if combined["artifact_status"] != "RESOLVED":
            unresolved.append(artifact_id)
        artifacts.append(combined)
    body = {
        "schema": "grt-repository-reference-graph/v0.2", "runtime_release": "GRT-REFERENCE-WP3A.v1",
        "serialization_profile": SERIALIZATION_ID, "tree_hash": tree_hash, "observed_components": observations,
        "repository_artifacts": artifacts, "unresolved_artifact_ids": sorted(unresolved),
        "resolution_status": "RESOLVED" if not unresolved else "PARTIAL",
        "authority_effect": "NONE_REFERENCE_OBSERVATION_ONLY", "active_enforcement": "NONE",
    }
    return {**body, "canonical_hash": canonical_sha256(body)}


def scan_repository_tree(
    repository_root: Path | str,
    *,
    commit: str,
    bindings_by_path: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Adapter over the existing v0.1 exact `git ls-tree` inventory substrate."""
    root = Path(repository_root)
    if not _HEX40.fullmatch(commit):
        raise ReferenceRuntimeError("GRT_REFERENCE_COMMIT_INVALID")
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{commit}^{{tree}}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise ReferenceRuntimeError("GRT_REFERENCE_TREE_RESOLUTION_FAILED")
    tree_hash = completed.stdout.strip()
    if not _HEX40.fullmatch(tree_hash):
        raise ReferenceRuntimeError("GRT_REFERENCE_TREE_INVALID")
    inventory = tracked_inventory(root, commit=commit)
    components = [
        {"path": row["path"], "content_hash": row["blob_hash"], "component_type": "file"}
        for row in inventory
    ]
    graph = build_reference_graph(tree_hash=tree_hash, components=components, bindings_by_path=bindings_by_path)
    return {**graph, "source_commit": commit}


def replay_b0_baseline(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    validate_baseline_members(rows)
    membership_hash = baseline_membership_sha256(rows)
    if len(rows) != B0_MEMBER_COUNT or membership_hash != B0_MEMBERSHIP_SHA256:
        raise ReferenceRuntimeError("GRT_REFERENCE_B0_REPLAY_MISMATCH")
    return {
        "schema": "grt-reference-b0-replay/v0.2", "runtime_release": "GRT-REFERENCE-WP3A.v1",
        "member_count": len(rows), "membership_sha256": membership_hash,
        "pending_mapping_count": sum(1 for row in rows if row.get("mapping_status") != "MAPPED"),
        "authority_effect": "NONE_HISTORICAL_REPLAY_ONLY", "active_enforcement": "NONE", "status": "PASS",
    }

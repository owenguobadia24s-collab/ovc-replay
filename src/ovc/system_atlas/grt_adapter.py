from __future__ import annotations

import re
import subprocess
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from ovc.programme_genesis._topology_engine import build_repository_topology

from .canonical import canonical_sha256, logical_id


class AtlasGRTAdapterError(ValueError):
    """Raised when GRT observations cannot be adapted without semantic promotion."""


EXTRACTOR_ID = "atlas.extractor.grt-exact-tree.v0.1"
EXTRACTOR_VERSION = "0.1"
RAW_SET_SCHEMA = "ovc-atlas-raw-observation-set/v1"
GRT_EVIDENCE_CLASSES = frozenset(
    {
        "SOURCE_EXPLICIT",
        "LINEAGE_EXPLICIT",
        "PATH_AND_CONTENT_CORROBORATED",
        "TEST_CORROBORATED",
        "IMPORT_CORROBORATED",
        "CANDIDATE_RELATION",
        "INFERRED",
        "UNRESOLVED",
    }
)
HIGH_RISK_GRT_PREDICATES = frozenset({"OWNED_BY", "GOVERNED_BY"})
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise AtlasGRTAdapterError(code)


def _path(value: object) -> str:
    candidate = str(value or "").replace("\\", "/")
    parsed = PurePosixPath(candidate)
    _require(bool(candidate) and not parsed.is_absolute() and ".." not in parsed.parts, "ATLAS_GRT_SOURCE_PATH_INVALID")
    return parsed.as_posix()


def _tree_for_commit(repository_root: Path, commit: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository_root), "rev-parse", f"{commit}^{{tree}}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    _require(completed.returncode == 0, "ATLAS_GRT_TREE_RESOLUTION_FAILED")
    tree = completed.stdout.strip()
    _require(_SHA40.fullmatch(tree) is not None, "ATLAS_GRT_TREE_INVALID")
    return tree


def _tracked_worktree_is_clean(repository_root: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repository_root), "status", "--porcelain", "--untracked-files=no"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    _require(completed.returncode == 0, "ATLAS_GRT_WORKTREE_STATUS_FAILED")
    return not completed.stdout.strip()


def _observation(
    *,
    repository_commit: str,
    repository_tree: str,
    source_path: str,
    source_blob_sha: str,
    locator: str,
    observation_type: str,
    raw_subject: str,
    raw_predicate: str,
    raw_object: Any,
    scope_hints: Mapping[str, Any],
    parse_status: str,
    evidence_class: str,
) -> dict[str, Any]:
    _require(_SHA40.fullmatch(repository_commit) is not None, "ATLAS_GRT_COMMIT_INVALID")
    _require(_SHA40.fullmatch(repository_tree) is not None, "ATLAS_GRT_TREE_INVALID")
    normalized_path = _path(source_path)
    _require(_SHA40.fullmatch(source_blob_sha) is not None, "ATLAS_GRT_BLOB_INVALID")
    _require(evidence_class in GRT_EVIDENCE_CLASSES, "ATLAS_GRT_EVIDENCE_CLASS_INVALID")
    _require(parse_status in {"PARSED", "PARTIAL", "UNRESOLVED"}, "ATLAS_GRT_PARSE_STATUS_INVALID")
    content = {
        "observation_type": observation_type,
        "raw_subject": raw_subject,
        "raw_predicate": raw_predicate,
        "raw_object": deepcopy(raw_object),
        "scope_hints": deepcopy(dict(scope_hints)),
        "parse_status": parse_status,
        "evidence_class": evidence_class,
    }
    normalized_content_hash = canonical_sha256(content)
    identity = {
        "extractor_id": EXTRACTOR_ID,
        "extractor_version": EXTRACTOR_VERSION,
        "repository_commit": repository_commit,
        "repository_tree": repository_tree,
        "source_path": normalized_path,
        "source_blob_sha": source_blob_sha,
        "locator": locator,
        "normalized_content_hash": normalized_content_hash,
    }
    return {
        "observation_id": logical_id("observation", identity),
        **identity,
        **content,
        "canonical_promotion": "DENIED_PENDING_PREDICATE_AUTHORITY_RESOLUTION",
        "authority_effect": "NONE_RAW_OBSERVATION_ONLY",
    }


def adapt_grt_topology(*, read_model: Mapping[str, Any], repository_tree: str) -> dict[str, Any]:
    """Adapt the GRT v0.1 exact-tree read model without resolving semantic truth."""
    _require(read_model.get("schema") == "ovc-genesis-repository-topology-read-model/v1", "ATLAS_GRT_READ_MODEL_SCHEMA_INVALID")
    _require(read_model.get("authority_effect") == "NONE_DERIVED_REPLACEABLE_READ_MODEL", "ATLAS_GRT_INPUT_AUTHORITY_INVALID")
    portfolio = read_model.get("portfolio")
    metadata = read_model.get("build_metadata")
    _require(isinstance(portfolio, Mapping) and isinstance(metadata, Mapping), "ATLAS_GRT_INPUT_IDENTITY_MISSING")
    commit = str(portfolio.get("source_commit", ""))
    _require(commit == str(metadata.get("source_commit", "")) and _SHA40.fullmatch(commit) is not None, "ATLAS_GRT_COMMIT_BINDING_INVALID")
    _require(_SHA40.fullmatch(repository_tree) is not None, "ATLAS_GRT_TREE_INVALID")

    components = read_model.get("components")
    edges = read_model.get("component_dependencies")
    programmes = read_model.get("programmes", [])
    _require(isinstance(components, Sequence) and not isinstance(components, (str, bytes)), "ATLAS_GRT_COMPONENTS_INVALID")
    _require(isinstance(edges, Sequence) and not isinstance(edges, (str, bytes)), "ATLAS_GRT_EDGES_INVALID")
    _require(isinstance(programmes, Sequence) and not isinstance(programmes, (str, bytes)), "ATLAS_GRT_PROGRAMMES_INVALID")
    by_id: dict[str, Mapping[str, Any]] = {}
    by_path: dict[str, Mapping[str, Any]] = {}
    programme_ids = {
        f"programme:{row.get('programme_id', '')}"
        for row in programmes
        if isinstance(row, Mapping) and row.get("programme_id")
    }
    observations: list[dict[str, Any]] = []
    physical_components: list[dict[str, Any]] = []

    for component in sorted(components, key=lambda row: str(row.get("component_id", ""))):
        _require(isinstance(component, Mapping), "ATLAS_GRT_COMPONENT_INVALID")
        component_id = str(component.get("component_id", ""))
        path = _path(component.get("path"))
        blob = str(component.get("blob_hash", ""))
        _require(bool(component_id) and _SHA40.fullmatch(blob) is not None, "ATLAS_GRT_COMPONENT_IDENTITY_INVALID")
        _require(component_id not in by_id and path not in by_path, "ATLAS_GRT_COMPONENT_DUPLICATE")
        by_id[component_id] = component
        by_path[path] = component
        observation = _observation(
            repository_commit=commit,
            repository_tree=repository_tree,
            source_path=path,
            source_blob_sha=blob,
            locator=f"git:{repository_tree}:{path}",
            observation_type="PHYSICAL_COMPONENT",
            raw_subject=component_id,
            raw_predicate="PRESENT_AT_PATH",
            raw_object={"path": path, "component_type": str(component.get("component_type", "UNRESOLVED"))},
            scope_hints={"git_tree": repository_tree},
            parse_status="PARSED",
            evidence_class="PATH_AND_CONTENT_CORROBORATED",
        )
        observations.append(observation)
        physical_components.append(
            {
                "component_id": component_id,
                "path": path,
                "blob_hash": blob,
                "component_type": str(component.get("component_type", "UNRESOLVED")),
                "observation_id": observation["observation_id"],
                "resolution_status": "OBSERVED_ONLY",
                "authority_effect": "NONE_PHYSICAL_OBSERVATION_ONLY",
            }
        )

    component_edges: list[dict[str, Any]] = []
    for edge in sorted(edges, key=lambda row: str(row.get("edge_id", ""))):
        _require(isinstance(edge, Mapping), "ATLAS_GRT_EDGE_INVALID")
        subject = str(edge.get("from_id", ""))
        object_id = str(edge.get("to_id", ""))
        predicate = str(edge.get("edge_type", ""))
        evidence_class = str(edge.get("evidence_class", ""))
        valid_endpoints = set(by_id) | programme_ids
        _require(subject in valid_endpoints and object_id in valid_endpoints, "ATLAS_GRT_EDGE_ENDPOINT_INVALID")
        _require(evidence_class in GRT_EVIDENCE_CLASSES, "ATLAS_GRT_EVIDENCE_CLASS_INVALID")
        source_ref = _path(edge.get("source_ref"))
        source = by_path.get(source_ref)
        _require(source is not None, "ATLAS_GRT_EDGE_SOURCE_NOT_IN_EXACT_TREE")
        observation = _observation(
            repository_commit=commit,
            repository_tree=repository_tree,
            source_path=source_ref,
            source_blob_sha=str(source["blob_hash"]),
            locator=f"grt-edge:{edge.get('edge_id', '')}",
            observation_type="COMPONENT_RELATIONSHIP",
            raw_subject=subject,
            raw_predicate=predicate,
            raw_object=object_id,
            scope_hints={"git_tree": repository_tree},
            parse_status="UNRESOLVED" if evidence_class == "UNRESOLVED" else "PARSED",
            evidence_class=evidence_class,
        )
        observations.append(observation)
        component_edges.append(
            {
                "edge_id": str(edge.get("edge_id", "")),
                "from_id": subject,
                "to_id": object_id,
                "grt_predicate": predicate,
                "evidence_class": evidence_class,
                "observation_id": observation["observation_id"],
                "resolution_status": "UNRESOLVED" if evidence_class == "UNRESOLVED" else "OBSERVED_ONLY",
                "high_risk_semantic_promotion": "DENIED" if predicate in HIGH_RISK_GRT_PREDICATES else "NOT_ATTEMPTED",
                "authority_effect": "NONE_COMPONENT_EDGE_OBSERVATION_ONLY",
            }
        )

    observations.sort(key=lambda row: row["observation_id"])
    physical_components.sort(key=lambda row: row["component_id"])
    component_edges.sort(key=lambda row: row["edge_id"])
    body = {
        "schema": RAW_SET_SCHEMA,
        "extractor_id": EXTRACTOR_ID,
        "extractor_version": EXTRACTOR_VERSION,
        "repository_commit": commit,
        "repository_tree": repository_tree,
        "grt_programme_id": str(read_model.get("programme_id", "")),
        "grt_topology_sha256": str(read_model.get("topology_sha256", "")),
        "raw_observations": observations,
        "physical_components": physical_components,
        "component_edges": component_edges,
        "canonical_assertions": [],
        "completeness": {
            "grt_component_count": len(components),
            "adapted_component_count": len(physical_components),
            "grt_component_edge_count": len(edges),
            "adapted_component_edge_count": len(component_edges),
        },
        "court_record_status": "EXACT_GIT_TREE",
        "authority_effect": "NONE_RAW_OBSERVATION_SET_ONLY",
    }
    return {**body, "raw_observation_set_hash": canonical_sha256(body)}


def scan_grt_exact_tree(repository_root: Path | str, *, commit: str = "HEAD", rule_pack: Mapping[str, Any] | None = None) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    resolved = subprocess.run(
        ["git", "-C", str(root), "rev-parse", commit],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    _require(resolved.returncode == 0, "ATLAS_GRT_COMMIT_RESOLUTION_FAILED")
    source_commit = resolved.stdout.strip()
    _require(_SHA40.fullmatch(source_commit) is not None, "ATLAS_GRT_COMMIT_INVALID")
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    _require(head.returncode == 0, "ATLAS_GRT_HEAD_RESOLUTION_FAILED")
    if source_commit == head.stdout.strip():
        _require(_tracked_worktree_is_clean(root), "ATLAS_GRT_EXACT_TREE_WORKTREE_DIRTY")
    read_model = build_repository_topology(root, ref=source_commit, rule_pack=rule_pack)
    return adapt_grt_topology(read_model=read_model, repository_tree=_tree_for_commit(root, source_commit))

"""Validation for bounded, presentation-only Atlas repository projections."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def canonical_projection_hash(projection: dict[str, Any]) -> str:
    payload = json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def load_and_validate_projection(path: Path, repo_root: Path) -> dict[str, Any]:
    projection = json.loads(path.read_text(encoding="utf-8"))
    if projection["qualification_class"] != "ACTUAL_REPOSITORY_SHADOW_NOT_CONSOLE_SOURCE":
        raise ValueError("projection qualification class is not presentation-only")
    if projection["authority_effect"] != "NONE_PRESENTATION_ONLY":
        raise ValueError("projection attempts an authority effect")
    if projection["current_pointer_published"] or projection["research_console_binding_created"]:
        raise ValueError("projection attempts a forbidden publication or Console binding")

    tree = subprocess.run(
        ["git", "rev-parse", f'{projection["source_commit"]}^{{tree}}'],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if tree != projection["source_tree"]:
        raise ValueError("source commit/tree mismatch")

    node_ids = {node["id"] for node in projection["nodes"]}
    if len(node_ids) != len(projection["nodes"]):
        raise ValueError("duplicate node id")
    for node in projection["nodes"]:
        source = node["source"]
        result = subprocess.run(
            ["git", "ls-tree", projection["source_commit"], "--", source["path"]],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if not result or result.split()[2] != source["blob"]:
            raise ValueError(f'source binding mismatch: {source["path"]}')
    for edge in projection["edges"]:
        if edge["source"] not in node_ids or edge["target"] not in node_ids:
            raise ValueError(f'dangling edge: {edge["id"]}')
    for trace in projection["traces"]:
        if not trace["node_ids"] or not set(trace["node_ids"]).issubset(node_ids):
            raise ValueError(f'invalid trace: {trace["id"]}')

    projection["logical_hash"] = canonical_projection_hash(projection)
    return projection


def load_and_validate_workbench_projection(path: Path, repo_root: Path) -> dict[str, Any]:
    projection = load_and_validate_projection(path, repo_root)
    if projection.get("schema") != "ovc-system-atlas-workbench-projection/v1":
        raise ValueError("workbench projection schema mismatch")
    if projection.get("reality_class") != "CURRENT":
        raise ValueError("workbench reality class is not CURRENT")

    node_ids = {node["id"] for node in projection["nodes"]}
    surface_ids = {surface["id"] for surface in projection.get("surface_definitions", [])}
    if surface_ids != {"architecture", "research", "execution", "authority", "repository", "history"}:
        raise ValueError("principal workbench surfaces are incomplete")
    for surface in projection["surface_definitions"]:
        if not set(surface["node_ids"]).issubset(node_ids):
            raise ValueError(f'invalid surface membership: {surface["id"]}')

    query_ids = {query["id"] for query in projection.get("query_definitions", [])}
    expected_queries = {"SEARCH", "TRACE", "DEPENDENCY", "IMPACT", "EXPLAIN", "AUTHORITY", "OWNERSHIP", "WHY_BLOCKED", "HISTORY", "DIFF"}
    if query_ids != expected_queries:
        raise ValueError("workbench query catalogue is incomplete")
    if any(query.get("representations") != ["GRAPH", "TABLE"] for query in projection["query_definitions"]):
        raise ValueError("query graph/table alternative is incomplete")
    if projection.get("inspector_tabs") != ["Overview", "Relations", "Implementation", "Authority", "Evidence", "History"]:
        raise ValueError("Inspector contract is incomplete")
    if not any(node.get("depth") == 4 for node in projection["nodes"]):
        raise ValueError("L4 drill-down is absent")

    deep_link = projection.get("deep_link_contract", {})
    if deep_link.get("source_mutation_effect") != "NONE" or not deep_link.get("typed_context_only"):
        raise ValueError("deep-link contract attempts a source mutation")
    presentation = projection.get("presentation_state", {})
    if presentation.get("authority_effect") != "NONE" or presentation.get("storage") != "BROWSER_LOCAL_ONLY":
        raise ValueError("presentation state crosses the authority boundary")
    return projection

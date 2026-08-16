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

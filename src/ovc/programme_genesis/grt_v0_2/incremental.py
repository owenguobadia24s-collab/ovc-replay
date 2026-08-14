"""GRT2 exact incremental fallback runtime.

The incremental provider is correctness-first.  When bounded cache/impact evidence is
not sufficient, it deterministically escalates to the full reference graph.  This
provides a semantically exact incremental surface without inventing a permissive
optimization path; later optimisation may replace the fallback only after differential
qualification.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .reference import build_reference_graph, scan_repository_tree
from .serialization import canonical_sha256

RUNTIME_RELEASE = "GRT-INCREMENTAL-WP3D.v1-REFERENCE-FALLBACK"


def build_incremental_graph(
    *,
    tree_hash: str,
    components: Sequence[Mapping[str, Any]],
    bindings_by_path: Mapping[str, Mapping[str, Any]] | None = None,
    changed_paths: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Return the exact reference graph through the mandatory safe fallback.

    ``changed_paths`` is accepted as impact metadata only.  Until a qualified cache
    partition is supplied, no component may be omitted from semantic evaluation.
    """
    graph = build_reference_graph(
        tree_hash=tree_hash,
        components=components,
        bindings_by_path=bindings_by_path,
    )
    body = {
        "schema": "grt-incremental-result/v0.2",
        "runtime_release": RUNTIME_RELEASE,
        "strategy": "FULL_REFERENCE_FALLBACK",
        "changed_paths": sorted(set(changed_paths or ())),
        "reference_canonical_hash": graph["canonical_hash"],
        "semantic_graph": graph,
        "authority_effect": "NONE_INCREMENTAL_SHADOW_ONLY",
    }
    return {**body, "canonical_hash": canonical_sha256(body)}


def scan_repository_tree_incremental(
    repository_root: str,
    *,
    commit: str,
    bindings_by_path: Mapping[str, Mapping[str, Any]] | None = None,
    changed_paths: Sequence[str] | None = None,
) -> dict[str, Any]:
    graph = scan_repository_tree(
        repository_root,
        commit=commit,
        bindings_by_path=bindings_by_path,
    )
    body = {
        "schema": "grt-incremental-result/v0.2",
        "runtime_release": RUNTIME_RELEASE,
        "strategy": "FULL_REFERENCE_FALLBACK",
        "changed_paths": sorted(set(changed_paths or ())),
        "reference_canonical_hash": graph["canonical_hash"],
        "semantic_graph": graph,
        "authority_effect": "NONE_INCREMENTAL_SHADOW_ONLY",
    }
    return {**body, "canonical_hash": canonical_sha256(body)}

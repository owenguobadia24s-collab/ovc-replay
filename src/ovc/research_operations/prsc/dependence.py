from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from ovc.research_operations.canonical import canonical_sha256
from ovc.research_operations.ec1_path1 import DependenceEdge, EvidenceDependenceGraph
from .contracts import PRSCContractError


@dataclass(frozen=True)
class DependenceGraphView:
    """Read-only candidate-scoped projection of the EC1 owner graph."""
    candidate_unit_ids: tuple[str, ...]
    owner_edges: tuple[DependenceEdge, ...]
    unresolved_unit_ids: tuple[str, ...]

    @property
    def semantic_sha256(self) -> str:
        return canonical_sha256({
            "candidate_unit_ids": list(self.candidate_unit_ids),
            "owner_edges": [{"left": e.left, "right": e.right, "edge_type": e.edge_type} for e in self.owner_edges],
            "unresolved_unit_ids": list(self.unresolved_unit_ids),
            "graph_depth": 1,
            "independence_default": "UNKNOWN",
        })


def adapt_evidence_dependence_graph(graph: EvidenceDependenceGraph, candidate_unit_ids: Iterable[str]) -> DependenceGraphView:
    ids = tuple(sorted({str(v) for v in candidate_unit_ids if str(v)}))
    if not ids:
        raise PRSCContractError("PRSC_DEPENDENCE_EMPTY_CANDIDATE_UNIVERSE")
    if graph.stored_graph_depth != 1:
        raise PRSCContractError("PRSC_DEPENDENCE_OWNER_GRAPH_NOT_DIRECT_EDGE")
    universe = set(ids)
    edges = tuple(sorted(
        (e for e in graph.edges if e.left in universe and e.right in universe),
        key=lambda e: (min(e.left, e.right), max(e.left, e.right), e.edge_type),
    ))
    touched = {v for e in edges for v in (e.left, e.right)}
    return DependenceGraphView(ids, edges, tuple(sorted(universe - touched)))


def owner_connected_components(view: DependenceGraphView) -> tuple[tuple[str, ...], ...]:
    nodes = {v for e in view.owner_edges for v in (e.left, e.right)}
    adjacency = {n: set() for n in nodes}
    for edge in view.owner_edges:
        adjacency[edge.left].add(edge.right)
        adjacency[edge.right].add(edge.left)
    components: list[tuple[str, ...]] = []
    remaining = set(nodes)
    while remaining:
        root = min(remaining)
        stack = [root]
        seen: set[str] = set()
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(sorted(adjacency[node] - seen, reverse=True))
        remaining -= seen
        components.append(tuple(sorted(seen)))
    return tuple(sorted(components))


def build_candidate_dependence_profile(graph: EvidenceDependenceGraph, candidate_unit_ids: Iterable[str]) -> dict:
    view = adapt_evidence_dependence_graph(graph, candidate_unit_ids)
    components = owner_connected_components(view)
    return {
        "schema": "ovc-prsc-candidate-dependence-profile/v0.1",
        "candidate_unit_ids": list(view.candidate_unit_ids),
        "owner_graph_depth": 1,
        "owner_edge_count": len(view.owner_edges),
        "owner_components": [list(c) for c in components],
        "owner_component_count": len(components),
        "unresolved_unit_ids": list(view.unresolved_unit_ids),
        "independence_claim": "NOT_ESTABLISHED",
        "no_edge_semantics": "INDEPENDENCE_UNKNOWN",
        "authority_effect": "NONE",
        "semantic_sha256": view.semantic_sha256,
    }


def build_inference_block_manifest(*, graph: EvidenceDependenceGraph, candidate_unit_ids: Iterable[str], blocks: Mapping[str, Sequence[str]], block_source: str) -> dict:
    view = adapt_evidence_dependence_graph(graph, candidate_unit_ids)
    if not block_source:
        raise PRSCContractError("PRSC_BLOCK_SOURCE_REQUIRED")
    normalized: dict[str, tuple[str, ...]] = {}
    seen: set[str] = set()
    for block_id, values in blocks.items():
        bid = str(block_id).strip()
        members = tuple(sorted({str(v) for v in values if str(v)}))
        if not bid or not members:
            raise PRSCContractError("PRSC_BLOCK_EMPTY")
        collision = seen & set(members)
        if collision:
            raise PRSCContractError(f"PRSC_BLOCK_DUPLICATE_UNIT:{','.join(sorted(collision))}")
        seen.update(members)
        normalized[bid] = members
    expected = set(view.candidate_unit_ids)
    if seen != expected:
        raise PRSCContractError(f"PRSC_BLOCK_ACCOUNTING_MISMATCH:missing={sorted(expected-seen)}:extra={sorted(seen-expected)}")
    membership = {unit: block_id for block_id, members in normalized.items() for unit in members}
    for edge in view.owner_edges:
        if membership[edge.left] != membership[edge.right]:
            raise PRSCContractError(f"PRSC_DEPENDENCE_COMPONENT_SPLIT:{edge.left}:{edge.right}:{edge.edge_type}")
    payload = {
        "schema": "ovc-prsc-inference-block-manifest/v0.1",
        "block_source": block_source,
        "candidate_unit_ids": list(view.candidate_unit_ids),
        "blocks": [{"block_id": bid, "unit_ids": list(normalized[bid])} for bid in sorted(normalized)],
        "owner_edge_count": len(view.owner_edges),
        "unresolved_unit_ids": list(view.unresolved_unit_ids),
        "graph_absence_does_not_imply_independence": True,
        "authority_effect": "NONE",
    }
    payload["manifest_id"] = canonical_sha256(payload)
    return payload


def leave_one_component_out(manifest: Mapping[str, object]) -> tuple[dict, ...]:
    blocks = list(manifest.get("blocks", []))
    if not blocks:
        raise PRSCContractError("PRSC_LOCO_BLOCKS_REQUIRED")
    all_units = tuple(str(v) for v in manifest.get("candidate_unit_ids", []))
    out: list[dict] = []
    for block in blocks:
        omitted = tuple(str(v) for v in block["unit_ids"])
        omitted_set = set(omitted)
        remaining = tuple(v for v in all_units if v not in omitted_set)
        out.append({"omitted_block_id": str(block["block_id"]), "omitted_unit_ids": list(omitted), "remaining_unit_ids": list(remaining), "remaining_count": len(remaining)})
    return tuple(out)

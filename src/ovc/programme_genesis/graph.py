from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from copy import deepcopy
from typing import Any, Iterable, Mapping


class GraphValidationError(ValueError):
    """Raised when a typed dependency graph violates frozen invariants."""


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _find_cycles(adjacency: Mapping[str, set[str]]) -> list[list[str]]:
    cycles: set[tuple[str, ...]] = set()
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def canonical_cycle(path: list[str]) -> tuple[str, ...]:
        body = path[:-1]
        rotations = [tuple(body[index:] + body[:index]) for index in range(len(body))]
        smallest = min(rotations)
        return smallest + (smallest[0],)

    def visit(node: str) -> None:
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for neighbour in sorted(adjacency.get(node, set())):
            if neighbour in visiting:
                start = stack.index(neighbour)
                cycles.add(canonical_cycle(stack[start:] + [neighbour]))
            elif neighbour not in visited:
                visit(neighbour)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in sorted(adjacency):
        visit(node)
    return [list(cycle) for cycle in sorted(cycles)]


def validate_graph(
    nodes: Iterable[Mapping[str, Any]],
    edges: Iterable[Mapping[str, Any]],
    edge_type_registry: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    node_rows = [deepcopy(dict(node)) for node in nodes]
    edge_rows = [deepcopy(dict(edge)) for edge in edges]
    findings: list[dict[str, Any]] = []

    node_ids = [node.get("node_id") for node in node_rows]
    duplicate_nodes = sorted({node_id for node_id in node_ids if node_ids.count(node_id) > 1})
    if duplicate_nodes:
        findings.append({"code": "DUPLICATE_NODE_ID", "severity": "BLOCK", "values": duplicate_nodes})
    known_nodes = set(node_ids)

    edge_ids = [edge.get("edge_id") for edge in edge_rows]
    duplicate_edges = sorted({edge_id for edge_id in edge_ids if edge_ids.count(edge_id) > 1})
    if duplicate_edges:
        findings.append({"code": "DUPLICATE_EDGE_ID", "severity": "BLOCK", "values": duplicate_edges})

    hard_adjacency: dict[str, set[str]] = defaultdict(set)
    all_adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in sorted(edge_rows, key=lambda item: str(item.get("edge_id"))):
        edge_id = edge.get("edge_id")
        from_node = edge.get("from_node")
        to_node = edge.get("to_node")
        edge_type = edge.get("edge_type")
        hardness = edge.get("hardness")
        source_kind = edge.get("source_kind")

        if from_node not in known_nodes or to_node not in known_nodes:
            findings.append({"code": "ORPHAN_EDGE_ENDPOINT", "severity": "BLOCK", "edge_id": edge_id, "from_node": from_node, "to_node": to_node})
            continue
        if from_node == to_node:
            findings.append({"code": "SELF_EDGE", "severity": "BLOCK", "edge_id": edge_id})
        rule = edge_type_registry.get(str(edge_type))
        if rule is None:
            findings.append({"code": "UNKNOWN_EDGE_TYPE", "severity": "BLOCK", "edge_id": edge_id, "edge_type": edge_type})
            continue
        if hardness not in rule.get("allowed_hardness", []):
            findings.append({"code": "INVALID_EDGE_HARDNESS", "severity": "BLOCK", "edge_id": edge_id, "hardness": hardness})
        if hardness == "HARD" and rule.get("hard_requires_source_explicit") and source_kind != "SOURCE_EXPLICIT":
            findings.append({"code": "INFERRED_HARD_PREREQUISITE", "severity": "QUARANTINE", "edge_id": edge_id})
        if edge.get("authority_effect") != "NONE":
            findings.append({"code": "GRAPH_AUTHORITY_GRANT", "severity": "QUARANTINE", "edge_id": edge_id, "authority_effect": edge.get("authority_effect")})
        if not edge.get("source_refs"):
            findings.append({"code": "MISSING_EDGE_SOURCE", "severity": "BLOCK", "edge_id": edge_id})

        all_adjacency[from_node].add(to_node)
        all_adjacency.setdefault(to_node, set())
        if hardness == "HARD" and edge_type in {"REQUIRES", "GOVERNED_BY", "BLOCKED_BY", "CONSUMES"}:
            hard_adjacency[from_node].add(to_node)
            hard_adjacency.setdefault(to_node, set())

    hard_cycles = _find_cycles(hard_adjacency)
    for cycle in hard_cycles:
        findings.append({"code": "HARD_DEPENDENCY_CYCLE", "severity": "QUARANTINE", "cycle": cycle})
    all_cycles = _find_cycles(all_adjacency)
    soft_cycles = [cycle for cycle in all_cycles if cycle not in hard_cycles]
    for cycle in soft_cycles:
        findings.append({"code": "NON_HARD_CYCLE", "severity": "WARN", "cycle": cycle})

    blocking = [finding for finding in findings if finding["severity"] in {"BLOCK", "QUARANTINE"}]
    ordered_nodes = sorted(node_rows, key=lambda item: item["node_id"])
    ordered_edges = sorted(edge_rows, key=lambda item: item["edge_id"])
    snapshot = {"nodes": ordered_nodes, "edges": ordered_edges}
    return {
        "status": "PASS" if not blocking else "FAIL",
        "node_count": len(ordered_nodes),
        "edge_count": len(ordered_edges),
        "hard_cycle_count": len(hard_cycles),
        "non_hard_cycle_count": len(soft_cycles),
        "findings": findings,
        "authority_path_status": "PASS" if not any(finding["code"] == "GRAPH_AUTHORITY_GRANT" for finding in findings) else "FAIL",
        "graph_sha256": _digest(snapshot),
        "snapshot": snapshot,
    }


def impact_analysis(
    nodes: Iterable[Mapping[str, Any]],
    edges: Iterable[Mapping[str, Any]],
    changed_node_ids: Iterable[str],
) -> dict[str, Any]:
    node_rows = [dict(node) for node in nodes]
    edge_rows = [dict(edge) for edge in edges]
    known = {node["node_id"] for node in node_rows}
    changed = sorted(set(changed_node_ids))
    unknown = sorted(set(changed).difference(known))
    if unknown:
        raise GraphValidationError(f"unknown changed nodes: {unknown}")

    prerequisites: dict[str, set[str]] = defaultdict(set)
    dependents: dict[str, set[str]] = defaultdict(set)
    for edge in edge_rows:
        if edge.get("status") not in {"ACCEPTED", "PROPOSED"}:
            continue
        source = edge["from_node"]
        target = edge["to_node"]
        prerequisites[source].add(target)
        dependents[target].add(source)

    def traverse(start: Iterable[str], adjacency: Mapping[str, set[str]]) -> list[str]:
        seen = set(start)
        queue = deque(sorted(start))
        while queue:
            current = queue.popleft()
            for neighbour in sorted(adjacency.get(current, set())):
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append(neighbour)
        return sorted(seen.difference(start))

    upstream = traverse(changed, prerequisites)
    downstream = traverse(changed, dependents)
    result = {
        "changed_nodes": changed,
        "upstream_prerequisites": upstream,
        "downstream_impacted": downstream,
        "direct_downstream": sorted({node for changed_node in changed for node in dependents.get(changed_node, set())}),
        "authority_effect": "NONE_DERIVED_ANALYSIS_ONLY",
        "operator_decision_required_for_any_authority_change": True,
    }
    result["impact_sha256"] = _digest(result)
    return result

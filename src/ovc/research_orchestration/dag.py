from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Iterable

from .models import StageSpec
from .serialization import logical_sha256


class DagError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class CanonicalDag:
    stage_ids: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    order: tuple[str, ...]

    @property
    def logical_hash(self) -> str:
        return logical_sha256({
            "stage_ids": list(self.stage_ids),
            "edges": [list(edge) for edge in self.edges],
            "order": list(self.order),
        })

    def parents_of(self, stage_id: str) -> tuple[str, ...]:
        return tuple(parent for parent, child in self.edges if child == stage_id)

    def children_of(self, stage_id: str) -> tuple[str, ...]:
        return tuple(child for parent, child in self.edges if parent == stage_id)

    def blocked_descendants(self, blocked_stage_ids: Iterable[str]) -> tuple[str, ...]:
        blocked = set(blocked_stage_ids)
        unknown = blocked - set(self.stage_ids)
        if unknown:
            raise DagError("IROF_UNKNOWN_BLOCKED_STAGE", ",".join(sorted(unknown)))
        frontier = list(sorted(blocked))
        descendants: set[str] = set()
        while frontier:
            current = frontier.pop(0)
            for child in self.children_of(current):
                if child not in blocked and child not in descendants:
                    descendants.add(child)
                    frontier.append(child)
        return tuple(sorted(descendants))


def _stage_map(stage_specs: Iterable[StageSpec]) -> dict[str, StageSpec]:
    values = tuple(stage_specs)
    mapping = {stage.stage_id: stage for stage in values}
    if len(values) != len(mapping):
        raise DagError("IROF_DUPLICATE_STAGE_ID", "duplicate StageSpec identity")
    return mapping


def _topological_order(stage_ids: set[str], edges: set[tuple[str, str]]) -> tuple[str, ...]:
    indegree = {stage_id: 0 for stage_id in stage_ids}
    children: dict[str, set[str]] = {stage_id: set() for stage_id in stage_ids}
    for parent, child in edges:
        indegree[child] += 1
        children[parent].add(child)

    ready = [stage_id for stage_id, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        current = heapq.heappop(ready)
        order.append(current)
        for child in sorted(children[current]):
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(ready, child)

    if len(order) != len(stage_ids):
        cyclic = sorted(stage_id for stage_id, degree in indegree.items() if degree > 0)
        raise DagError("IROF_DEPENDENCY_CYCLE", ",".join(cyclic))
    return tuple(order)


def build_canonical_dag(*, stage_specs: Iterable[StageSpec], included_stage_ids: Iterable[str]) -> CanonicalDag:
    mapping = _stage_map(stage_specs)
    included_values = tuple(included_stage_ids)
    included = set(included_values)
    if len(included_values) != len(included):
        raise DagError("IROF_DUPLICATE_PROFILE_STAGE", "profile contains duplicate stage identity")
    unknown = included - set(mapping)
    if unknown:
        raise DagError("IROF_PROFILE_UNKNOWN_STAGE", ",".join(sorted(unknown)))

    edges: set[tuple[str, str]] = set()
    for stage_id in sorted(included):
        stage = mapping[stage_id]
        for dep in sorted(stage.dependencies, key=lambda item: item.stage_id):
            parent = mapping.get(dep.stage_id)
            if parent is None:
                if dep.disposition == "REQUIRED":
                    raise DagError("IROF_UNKNOWN_REQUIRED_DEPENDENCY", f"{stage_id}<-{dep.stage_id}")
                continue
            present = dep.stage_id in included
            if dep.disposition == "REQUIRED" and not present:
                raise DagError("IROF_MISSING_REQUIRED_DEPENDENCY", f"{stage_id}<-{dep.stage_id}")
            if dep.disposition == "FORBIDDEN" and present:
                raise DagError("IROF_FORBIDDEN_DEPENDENCY", f"{stage_id}<-{dep.stage_id}")
            if not present:
                continue
            expected = set(dep.expected_output_types)
            if expected and not expected.issubset(set(parent.output_types)):
                missing = sorted(expected - set(parent.output_types))
                raise DagError("IROF_DEPENDENCY_OUTPUT_TYPE_MISMATCH", f"{stage_id}<-{dep.stage_id}:{','.join(missing)}")
            edges.add((dep.stage_id, stage_id))

    stage_ids = tuple(sorted(included))
    order = _topological_order(set(stage_ids), edges)
    return CanonicalDag(stage_ids=stage_ids, edges=tuple(sorted(edges)), order=order)

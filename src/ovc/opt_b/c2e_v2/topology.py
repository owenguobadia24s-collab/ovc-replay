"""Deterministic append-only episode topology for C2E v0.2."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .models import build_record


class TopologyError(ValueError):
    pass


class EpisodeTopology:
    def __init__(self) -> None:
        self._children: dict[str, set[str]] = defaultdict(set)
        self._edges: list[dict] = []

    def _reaches(self, start: str, target: str) -> bool:
        stack = [start]
        seen: set[str] = set()
        while stack:
            node = stack.pop()
            if node == target:
                return True
            if node in seen:
                continue
            seen.add(node)
            stack.extend(sorted(self._children.get(node, ())))
        return False

    def add_edge(self, *, edge_type: str, parent_episode_id: str, child_episode_id: str, boundary_event_id: str, effective_time: str, first_valid_time: str) -> dict:
        if edge_type not in {"NEST","RE_PARENT","SPLIT","MERGE"}:
            raise TopologyError("TOPOLOGY_EDGE_TYPE_INVALID")
        if parent_episode_id == child_episode_id or self._reaches(child_episode_id, parent_episode_id):
            raise TopologyError("C2E_TOPOLOGY_CYCLE")
        record = build_record("lineage_edge", {
            "edge_type":edge_type,"parent_episode_id":parent_episode_id,"child_episode_id":child_episode_id,
            "boundary_event_id":boundary_event_id,"effective_time":effective_time,"first_valid_time":first_valid_time,
            "authority":"INACTIVE_NONCANONICAL_SHADOW",
        })
        self._children[parent_episode_id].add(child_episode_id)
        self._edges.append(record)
        return record

    @property
    def edges(self) -> list[dict]:
        return [dict(item) for item in self._edges]

    def children(self, episode_id: str) -> tuple[str, ...]:
        return tuple(sorted(self._children.get(episode_id, ())))

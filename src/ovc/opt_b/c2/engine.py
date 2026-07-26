from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .adapter import accept_c1_record
from .containers import build_containers
from .levels import build_levels
from .persistence import apply_persistence
from .relations import build_relation_set
from .state import build_parallel_state
from .transitions import build_transition

_MAX_HISTORY = {"15M": 64, "2H_A_L": 48}


@dataclass(frozen=True)
class EngineResult:
    state: dict[str, Any]
    transition: dict[str, Any] | None
    levels: tuple[dict[str, Any], ...]
    containers: tuple[dict[str, Any], ...]
    relation_set: dict[str, Any]


class C2ScopeEngine:
    """Deterministic, gap-aware engine for one role/clock/side/evaluation scope."""

    def __init__(self, evaluation_scope_id: str):
        self.evaluation_scope_id = evaluation_scope_id
        self.history: list[dict[str, Any]] = []
        self.previous_record: dict[str, Any] | None = None
        self.previous_state: dict[str, Any] | None = None
        self._scope: tuple[str, str, str, str] | None = None
        self._active_swings: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _contiguous(previous: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
        return (
            previous["c1_release_id"] == current["c1_release_id"]
            and previous["clock"] == current["clock"]
            and previous["side"] == current["side"]
            and previous["close_time"] == current["open_time"]
        )

    def _reset(self) -> None:
        self.history = []
        self.previous_record = None
        self.previous_state = None
        self._active_swings = {}

    def process(
        self,
        record: Mapping[str, Any],
        *,
        parent_levels: Iterable[Mapping[str, Any]] | None = None,
    ) -> EngineResult:
        current = accept_c1_record(record)
        scope = (
            current["role"],
            current["clock"],
            current["side"],
            self.evaluation_scope_id,
        )
        if self._scope is None:
            self._scope = scope
        elif self._scope != scope:
            raise ValueError(f"SCOPE_ENGINE_DRIFT:{self._scope}:{scope}")
        if self.previous_record is not None and not self._contiguous(self.previous_record, current):
            self._reset()
            self._scope = scope

        self.history.append(current)
        self.history = self.history[-_MAX_HISTORY[current["clock"]] :]
        levels = build_levels(current, self.history)
        reconciled_levels: list[dict[str, Any]] = []
        for level in levels:
            kind = str(level["level_type"])
            if kind in {"SWING_HIGH", "SWING_LOW"}:
                if level.get("status") == "ACTIVE":
                    self._active_swings[kind] = level
                elif kind in self._active_swings:
                    level = self._active_swings[kind]
            reconciled_levels.append(level)

        parent_level_items = list(parent_levels or ())
        containers = build_containers(current, reconciled_levels, parent_level_items)
        relation_set = build_relation_set(
            current,
            reconciled_levels + parent_level_items,
            containers,
            self.previous_record,
            evaluation_scope_id=self.evaluation_scope_id,
        )
        structure = {
            "levels": reconciled_levels,
            "containers": containers,
            "relation_set": relation_set,
        }
        state = build_parallel_state(
            current,
            history=self.history,
            previous_record=self.previous_record,
            parent_levels=parent_level_items,
            evaluation_scope_id=self.evaluation_scope_id,
            structure=structure,
        )
        state = apply_persistence(state, self.previous_state)
        transition = build_transition(state, self.previous_state)
        self.previous_record = current
        self.previous_state = state
        return EngineResult(
            state=state,
            transition=transition,
            levels=tuple(reconciled_levels),
            containers=tuple(containers),
            relation_set=relation_set,
        )

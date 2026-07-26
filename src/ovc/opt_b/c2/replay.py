from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .persistence import apply_persistence
from .state import build_parallel_state
from .transitions import build_transition


DISCOVERY_RELEASE = "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1"
DEVELOPMENT_RELEASE = "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1"
_ALLOWED = {"DISCOVERY": DISCOVERY_RELEASE, "DEVELOPMENT": DEVELOPMENT_RELEASE}


class ReplayError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReplaySummary:
    role: str
    release_id: str
    input_records: int
    state_records: int
    transition_records: int
    rejected_records: int


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ReplayError(f"INVALID_JSONL:{path}:{line_number}") from exc
            if not isinstance(payload, dict):
                raise ReplayError(f"NON_OBJECT_RECORD:{path}:{line_number}")
            yield payload


def run_role_replay(*, role: str, release_id: str, input_path: Path, output_dir: Path) -> ReplaySummary:
    expected = _ALLOWED.get(role)
    if expected is None:
        raise ReplayError("WRONG_ROLE")
    if release_id != expected:
        raise ReplayError("WRONG_RELEASE_ID")
    if not input_path.is_file():
        raise ReplayError(f"MISSING_INPUT:{input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / f"{role.lower()}_states.jsonl"
    transition_path = output_dir / f"{role.lower()}_transitions.jsonl"
    previous: dict[str, Any] | None = None
    input_count = state_count = transition_count = rejected_count = 0

    with state_path.open("w", encoding="utf-8", newline="\n") as states, transition_path.open("w", encoding="utf-8", newline="\n") as transitions:
        for record in read_jsonl(input_path):
            input_count += 1
            try:
                current = apply_persistence(build_parallel_state(record), previous)
            except Exception:
                rejected_count += 1
                continue
            states.write(json.dumps(current, sort_keys=True, separators=(",", ":")) + "\n")
            state_count += 1
            transition = build_transition(current, previous)
            if transition is not None:
                transitions.write(json.dumps(transition, sort_keys=True, separators=(",", ":")) + "\n")
                transition_count += 1
            previous = current

    return ReplaySummary(role, release_id, input_count, state_count, transition_count, rejected_count)

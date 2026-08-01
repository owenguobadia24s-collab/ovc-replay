"""Deterministic gate packet records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .identity import canonical_sha256, normalize_relative_path


ALLOWED_DECISIONS = {"PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"}


@dataclass(frozen=True)
class GatePacket:
    gate_id: str
    plan_id: str
    plan_version: str
    programme_id: str
    packet_id: str
    baseline_commit: str
    candidate_commit: str
    authority_delta: str
    acceptance_conditions: tuple[str, ...]
    tests: tuple[str, ...]
    qa_status: str
    warnings: tuple[str, ...]
    unresolved_issues: tuple[str, ...]
    changed_files: tuple[str, ...]
    rollback: str
    recommended_decision: str
    next_packet: str | None

    def __post_init__(self) -> None:
        if self.recommended_decision not in ALLOWED_DECISIONS:
            raise ValueError("unsupported gate decision")
        if not self.acceptance_conditions or not self.tests or not self.rollback:
            raise ValueError("acceptance conditions, tests and rollback are required")
        normalized = tuple(sorted(normalize_relative_path(path) for path in self.changed_files))
        if normalized != tuple(sorted(self.changed_files)):
            raise ValueError("changed_files must be normalized and deterministically sorted")

    @property
    def gate_packet_id(self) -> str:
        return canonical_sha256(asdict(self), role="GATE_PACKET")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["gate_packet_id"] = self.gate_packet_id
        result["allowed_decisions"] = sorted(ALLOWED_DECISIONS)
        return result

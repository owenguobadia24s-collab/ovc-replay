"""Governed development decision records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .gates import ALLOWED_DECISIONS
from .identity import canonical_sha256


@dataclass(frozen=True)
class DecisionRecord:
    decision: str
    decision_authority: str
    plan_id: str
    plan_version: str
    programme_id: str
    packet_id: str
    gate_id: str
    baseline_commit: str
    candidate_commit: str
    tests: tuple[str, ...]
    qa_status: str
    authority_delta: str
    reserved_authority_delta: str
    rollback: str
    rationale: str
    next_packet: str | None

    def __post_init__(self) -> None:
        if self.decision not in ALLOWED_DECISIONS:
            raise ValueError("unsupported decision")
        if not self.decision_authority or not self.rollback or not self.rationale:
            raise ValueError("decision authority, rollback and rationale are required")
        if self.decision == "PASS" and not self.tests:
            raise ValueError("PASS decisions require test evidence")

    @property
    def decision_id(self) -> str:
        return canonical_sha256(asdict(self), role="DECISION_RECORD")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["decision_id"] = self.decision_id
        return result

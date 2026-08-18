from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

_ALLOWED = {
    "theory_lifecycle": frozenset({"SEED", "DRAFT", "FROZEN", "SUPERSEDED", "WITHDRAWN", "QUARANTINED"}),
    "evidence": frozenset({"UNTESTED", "EXPLORATORY", "SUPPORTED", "RESTRICTED", "CONTRADICTED", "SUPERSEDED", "WITHDRAWN", "UNRESOLVED"}),
    "p2_frontier": frozenset({"P2-0", "P2-1", "P2-2", "P2-3", "P2-4", "P2-5", "P2-6", "P2-7", "P2-8", "NOT_ENTERED", "BLOCKED", "DEFERRED", "ROUTED_AWAY", "QUARANTINED", "SUPERSEDED", "NOT_APPLICABLE"}),
    "formalisation": frozenset({"CAPTURE", "THEORY_FREEZE", "DECOMPOSITION", "DEFINITION", "PROTOCOL", "METHOD", "EXPERIMENT_SHELL", "PREREGISTRATION", "UNRESOLVED"}),
    "candidate_relation": frozenset({"NONE", "P2_6_ELIGIBLE", "PROPOSAL", "ADVERSARIAL_REVIEW", "RESEARCH_CANDIDATE_GENERATION_FROZEN", "UNRESOLVED"}),
    "currentness": frozenset({"CURRENT", "CURRENT_WITH_LIMITATION", "REASSESSMENT_REQUIRED", "SOURCE_GENERATION_ADVANCED", "AUTHORITY_FRONTIER_CHANGED", "HISTORICAL", "UNRESOLVED"}),
}


@dataclass(frozen=True, slots=True)
class TheoryStatePlanes:
    theory_lifecycle: str
    evidence: str
    p2_frontier: str
    formalisation: str
    candidate_relation: str
    currentness: str
    authority_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        validate_state_planes(
            {
                "theory_lifecycle": self.theory_lifecycle,
                "evidence": self.evidence,
                "p2_frontier": self.p2_frontier,
                "formalisation": self.formalisation,
                "candidate_relation": self.candidate_relation,
                "currentness": self.currentness,
            }
        )
        if len(set(self.authority_refs)) != len(self.authority_refs):
            raise ValueError("authority_refs must be unique")

    def as_dict(self) -> dict[str, object]:
        return {
            "theory_lifecycle": self.theory_lifecycle,
            "evidence": self.evidence,
            "p2_frontier": self.p2_frontier,
            "formalisation": self.formalisation,
            "candidate_relation": self.candidate_relation,
            "currentness": self.currentness,
            "authority_refs": list(self.authority_refs),
        }


def validate_state_planes(planes: Mapping[str, str]) -> None:
    unknown = set(planes).difference(_ALLOWED)
    if unknown:
        raise ValueError(f"unknown P2CTI state planes: {sorted(unknown)}")
    for plane, value in planes.items():
        if value not in _ALLOWED[plane]:
            raise ValueError(f"invalid {plane} value: {value}")


def infer_authority_from_state(*_: object, **__: object) -> None:
    """Deliberately impossible: authority is exact owner-reference evidence."""

    raise RuntimeError("P2CTI forbids authority inference from lifecycle/evidence/P2/currentness state")

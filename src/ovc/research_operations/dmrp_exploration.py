from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .canonical import canonical_sha256

INTAKE_DISPOSITIONS = frozenset({"READY_FOR_GUIDED_FORMALISATION", "TRAINING_REQUIRED", "UNFORMALISABLE", "DESCRIPTIVE_LANGUAGE_ONLY", "ABANDONED", "DEFERRED"})

class ExplorationAuthorityError(PermissionError):
    pass

@dataclass(frozen=True)
class NonEvidentiaryExploration:
    exploration_id: str
    research_mode: str
    notes: Mapping[str, Any]
    source_class: str = "SYNTHETIC_ONLY"
    authority_effect: str = "NONE"
    direct_candidate_promotion: str = "FORBIDDEN"

    def __post_init__(self) -> None:
        if self.source_class != "SYNTHETIC_ONLY" or self.authority_effect != "NONE" or self.direct_candidate_promotion != "FORBIDDEN":
            raise ExplorationAuthorityError("WP3 exploration is synthetic/non-evidentiary and cannot promote candidates")

    @property
    def semantic_sha256(self) -> str:
        return canonical_sha256({"exploration_id":self.exploration_id,"research_mode":self.research_mode,"notes":dict(self.notes),"source_class":self.source_class})

    def freeze_candidate(self) -> None:
        raise ExplorationAuthorityError("NON_EVIDENTIARY_EXPLORATION cannot freeze/admit a candidate")

@dataclass(frozen=True)
class Path2IntakeDisposition:
    intake_id: str
    disposition: str
    reason_codes: tuple[str, ...] = ()
    source_class: str = "SYNTHETIC_ONLY"
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.disposition not in INTAKE_DISPOSITIONS:
            raise ValueError("invalid Path-2 intake disposition")
        if self.source_class != "SYNTHETIC_ONLY" or self.authority_effect != "NONE":
            raise ExplorationAuthorityError("real-source Path-2 intake is not authorised by WP3")

@dataclass(frozen=True)
class Path2OperatorReadinessPack:
    pack_id: str
    training_fixture_ids: tuple[str, ...]
    guided_formalisation_fixture_ids: tuple[str, ...]
    intake_dispositions: tuple[Path2IntakeDisposition, ...]
    real_source_ready: bool = False
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.real_source_ready or self.authority_effect != "NONE":
            raise ExplorationAuthorityError("WP3 readiness pack cannot grant real-source Path-2 readiness/authority")
        if not self.training_fixture_ids or not self.guided_formalisation_fixture_ids:
            raise ValueError("synthetic training and guided-formalisation fixtures are required")

@dataclass(frozen=True)
class OperatorTouch:
    operation: str
    queue_age_seconds: int
    intervention_count: int
    abandoned: bool
    source_class: str = "SYNTHETIC_ONLY"

    def __post_init__(self) -> None:
        if self.queue_age_seconds < 0 or self.intervention_count < 0:
            raise ValueError("operator health values cannot be negative")

@dataclass
class Path2OperationalHealthLedger:
    touches: list[OperatorTouch] = field(default_factory=list)

    def add(self, touch: OperatorTouch) -> None:
        self.touches.append(touch)

    def summary(self) -> dict[str, Any]:
        n = len(self.touches)
        return {"touches":n,"abandoned":sum(1 for x in self.touches if x.abandoned),"interventions":sum(x.intervention_count for x in self.touches),"max_queue_age_seconds":max((x.queue_age_seconds for x in self.touches), default=0),"authority_effect":"NONE"}

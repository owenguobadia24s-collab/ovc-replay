from __future__ import annotations

from enum import Enum


class SkillMaturity(str, Enum):
    EXPERIMENTAL = "EXPERIMENTAL"
    QUALIFIED = "QUALIFIED"
    TRUSTED = "TRUSTED"


class SkillAvailability(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    AVAILABLE = "AVAILABLE"
    SUPERSEDED = "SUPERSEDED"
    QUARANTINED = "QUARANTINED"
    REVOKED = "REVOKED"


class SkillExecutionStatus(str, Enum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    QUARANTINED = "QUARANTINED"
    FAILED = "FAILED"
    NOT_EVALUABLE = "NOT_EVALUABLE"

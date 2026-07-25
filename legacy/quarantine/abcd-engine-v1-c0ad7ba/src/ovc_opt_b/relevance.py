from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Iterable, Mapping

from .models import ReferenceLevel


RELEVANCE_VERSION = "B-REF-0.2"


@dataclass(frozen=True, slots=True)
class RelevancePolicy:
    policy_id: str
    range_ttl: timedelta | None
    swing_ttl: timedelta | None
    retire_on_range_supersession: bool = True
    retire_on_acceptance: bool = True

    def ttl_for(self, level: ReferenceLevel) -> timedelta | None:
        if level.level_type.startswith("RANGE_"):
            return self.range_ttl
        if level.level_type.startswith("PRIOR_SWING_"):
            return self.swing_ttl
        raise ValueError(f"unsupported B-REF level type: {level.level_type}")


@dataclass(frozen=True, slots=True)
class LevelLifecycle:
    level_id: str
    relevant_from: datetime
    retired_at: datetime | None
    retirement_reason: str | None
    retirement_trigger_id: str | None
    policy_id: str
    lifecycle_id: str

    def is_relevant(self, candidate_open_time: datetime) -> bool:
        if candidate_open_time.tzinfo is None:
            raise ValueError("candidate time must be timezone-aware")
        return self.relevant_from <= candidate_open_time and (
            self.retired_at is None or candidate_open_time < self.retired_at
        )


SEED_RELEVANCE_POLICY = RelevancePolicy(
    policy_id="B-REF-0.2-SEED",
    range_ttl=timedelta(hours=8),
    swing_ttl=timedelta(hours=48),
)

RATIFIED_STRUCTURAL_ONLY_POLICY = RelevancePolicy(
    policy_id="B-REF-0.2-STRUCTURAL-ONLY",
    range_ttl=None,
    swing_ttl=None,
    retire_on_range_supersession=True,
    retire_on_acceptance=True,
)


def _lifecycle_id(
    level: ReferenceLevel,
    policy: RelevancePolicy,
    retired_at: datetime | None,
    reason: str | None,
    trigger_id: str | None,
) -> str:
    payload = {
        "relevance_version": RELEVANCE_VERSION,
        "level_id": level.level_id,
        "policy_id": policy.policy_id,
        "relevant_from": level.first_valid_time.astimezone(timezone.utc).isoformat(),
        "retired_at": retired_at.astimezone(timezone.utc).isoformat() if retired_at else None,
        "retirement_reason": reason,
        "retirement_trigger_id": trigger_id,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"lifecycle:{hashlib.sha256(canonical.encode()).hexdigest()}"


def build_level_lifecycles(
    levels: Iterable[ReferenceLevel],
    *,
    policy: RelevancePolicy = SEED_RELEVANCE_POLICY,
    acceptance_times: Mapping[str, tuple[datetime, str]] | None = None,
) -> tuple[LevelLifecycle, ...]:
    source = tuple(levels)
    acceptance_times = acceptance_times or {}
    next_same_type: dict[str, ReferenceLevel] = {}
    by_type: dict[str, list[ReferenceLevel]] = {}
    for level in source:
        by_type.setdefault(level.level_type, []).append(level)
    for typed in by_type.values():
        ordered = sorted(typed, key=lambda item: (item.first_valid_time, item.level_id))
        for current, following in zip(ordered, ordered[1:]):
            next_same_type[current.level_id] = following

    result: list[LevelLifecycle] = []
    reason_priority = {"ACCEPTED_THROUGH": 0, "RANGE_SUPERSEDED": 1, "MAXIMUM_AGE": 2}
    for level in source:
        candidates: list[tuple[datetime, str, str]] = []
        if policy.retire_on_range_supersession and level.level_type.startswith("RANGE_"):
            following = next_same_type.get(level.level_id)
            if following is not None:
                candidates.append((following.first_valid_time, "RANGE_SUPERSEDED", following.level_id))
        if policy.retire_on_acceptance and level.level_id in acceptance_times:
            accepted_at, record_id = acceptance_times[level.level_id]
            if accepted_at >= level.first_valid_time:
                candidates.append((accepted_at, "ACCEPTED_THROUGH", record_id))
        ttl = policy.ttl_for(level)
        if ttl is not None:
            candidates.append((level.first_valid_time + ttl, "MAXIMUM_AGE", policy.policy_id))

        if candidates:
            retired_at, reason, trigger_id = min(
                candidates, key=lambda item: (item[0], reason_priority[item[1]], item[2])
            )
        else:
            retired_at = reason = trigger_id = None
        result.append(
            LevelLifecycle(
                level_id=level.level_id,
                relevant_from=level.first_valid_time,
                retired_at=retired_at,
                retirement_reason=reason,
                retirement_trigger_id=trigger_id,
                policy_id=policy.policy_id,
                lifecycle_id=_lifecycle_id(level, policy, retired_at, reason, trigger_id),
            )
        )
    return tuple(sorted(result, key=lambda item: (item.relevant_from, item.level_id)))


def lifecycle_to_dict(lifecycle: LevelLifecycle) -> dict[str, object]:
    return {
        "lifecycle_id": lifecycle.lifecycle_id,
        "level_id": lifecycle.level_id,
        "relevance_version": RELEVANCE_VERSION,
        "policy_id": lifecycle.policy_id,
        "relevant_from": lifecycle.relevant_from.astimezone(timezone.utc).isoformat(),
        "retired_at": lifecycle.retired_at.astimezone(timezone.utc).isoformat() if lifecycle.retired_at else None,
        "retirement_reason": lifecycle.retirement_reason,
        "retirement_trigger_id": lifecycle.retirement_trigger_id,
    }

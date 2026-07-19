from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Iterable, Mapping

from .models import Bar


STATE_CONTRACT_VERSION = "B-STATE-0.2"


@dataclass(frozen=True, slots=True)
class StateEvidence:
    rank: int
    semantic_state: str
    direction: str
    level_id: str | None
    term_record_id: str


@dataclass(frozen=True, slots=True)
class CompoundTrigger:
    semantic_state: str
    rank: int
    support_level_ids: tuple[str, ...]
    trigger_term_record_ids: tuple[str, ...]
    conflicting_semantic_states: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PersistentState:
    semantic_state: str
    rank: int | None
    support_level_ids: tuple[str, ...]
    trigger_term_record_ids: tuple[str, ...]
    state_since: datetime


@dataclass(frozen=True, slots=True)
class NeutralExit:
    prior_state: str
    first_candidate_time: datetime
    confirmed_at: datetime
    reason: str
    input_bar_ids: tuple[str, str]
    exit_record_id: str


def resolve_compound_trigger(evidence: Iterable[StateEvidence]) -> CompoundTrigger | None:
    items = tuple(evidence)
    if not items:
        return None
    best_rank = min(item.rank for item in items)
    best = tuple(item for item in items if item.rank == best_rank)
    labels = tuple(sorted({item.semantic_state for item in best}))
    trigger_ids = tuple(sorted(item.term_record_id for item in best))
    levels = tuple(sorted({item.level_id for item in best if item.level_id is not None}))
    if best_rank == 1 or len(labels) != 1:
        return CompoundTrigger("AMBIGUOUS", 1, levels, trigger_ids, labels)
    return CompoundTrigger(labels[0], best_rank, levels, trigger_ids)


def apply_trigger(current: PersistentState, trigger: CompoundTrigger, at: datetime) -> tuple[PersistentState, str]:
    if trigger.semantic_state == "AMBIGUOUS":
        return PersistentState(
            "AMBIGUOUS", 1, trigger.support_level_ids, trigger.trigger_term_record_ids, at
        ), "CONFLICTING_TOP_PRECEDENCE_TRIGGER"
    if current.semantic_state in {"NEUTRAL", "AMBIGUOUS"}:
        return PersistentState(
            trigger.semantic_state,
            trigger.rank,
            trigger.support_level_ids,
            trigger.trigger_term_record_ids,
            at,
        ), "COMPOUND_STATE_ENTERED"
    if trigger.semantic_state == current.semantic_state or (
        current.rank is not None and trigger.rank <= current.rank
    ):
        return PersistentState(
            trigger.semantic_state,
            trigger.rank,
            trigger.support_level_ids,
            trigger.trigger_term_record_ids,
            at,
        ), "COMPOUND_STATE_REFRESHED" if trigger.semantic_state == current.semantic_state else "HIGHER_PRECEDENCE_TRANSITION"
    return current, "LOWER_PRECEDENCE_TRIGGER_SUPPRESSED"


def _direction(semantic_state: str) -> str | None:
    if semantic_state.endswith("_ABOVE") or semantic_state.endswith("_UP"):
        return "UP"
    if semantic_state.endswith("_BELOW") or semantic_state.endswith("_DOWN"):
        return "DOWN"
    return None


def neutral_exit_predicate(
    current: PersistentState,
    *,
    bar: Bar,
    previous_bar: Bar | None,
    atr: Decimal | None,
    level_prices: Mapping[str, Decimal],
    compression_failed: bool,
    coherent_trigger_present: bool,
) -> tuple[bool, str]:
    state = current.semantic_state
    if state == "NEUTRAL":
        return False, "ALREADY_NEUTRAL"
    if state == "AMBIGUOUS":
        return (not coherent_trigger_present), "AMBIGUITY_CLEARED"
    if state == "COMPRESSED":
        return compression_failed, "COMPRESSION_RELEASED"
    if state in {"DISPLACING_UP", "DISPLACING_DOWN"}:
        if previous_bar is None:
            return False, "INSUFFICIENT_EXIT_HISTORY"
        counter_close = bar.close <= previous_bar.close if state == "DISPLACING_UP" else bar.close >= previous_bar.close
        return counter_close, "DISPLACEMENT_EXHAUSTED"
    direction = _direction(state)
    if direction is None or not current.support_level_ids or atr is None:
        return False, "EXIT_NOT_EVALUABLE"
    prices = [level_prices[level_id] for level_id in current.support_level_ids]
    tolerance = max(Decimal(2) * bar.price_increment, Decimal("0.10") * atr)
    if direction == "UP":
        control = max(prices)
        return bar.close <= control - tolerance, "LEVEL_STATE_INVALIDATED"
    control = min(prices)
    return bar.close >= control + tolerance, "LEVEL_STATE_INVALIDATED"


def make_neutral_exit(
    prior: PersistentState,
    first_bar: Bar,
    confirming_bar: Bar,
    reason: str,
) -> NeutralExit:
    payload = {
        "state_contract_version": STATE_CONTRACT_VERSION,
        "prior_state": prior.semantic_state,
        "state_since": prior.state_since.astimezone(timezone.utc).isoformat(),
        "first_candidate_time": first_bar.close_time.astimezone(timezone.utc).isoformat(),
        "confirmed_at": confirming_bar.close_time.astimezone(timezone.utc).isoformat(),
        "reason": reason,
        "input_bar_ids": [first_bar.bar_id, confirming_bar.bar_id],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return NeutralExit(
        prior_state=prior.semantic_state,
        first_candidate_time=first_bar.close_time,
        confirmed_at=confirming_bar.close_time,
        reason=reason,
        input_bar_ids=(first_bar.bar_id, confirming_bar.bar_id),
        exit_record_id=f"neutral-exit:{hashlib.sha256(canonical.encode()).hexdigest()}",
    )

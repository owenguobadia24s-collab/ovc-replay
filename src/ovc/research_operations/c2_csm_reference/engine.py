from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal, ROUND_HALF_UP
import json
import math
from typing import Any, Mapping

from ovc.research_operations.canonical import canonical_json_bytes, canonical_sha256

from .models import (
    FormationLifecycleStep,
    R2Step,
    R3Step,
    R4State,
    R4Step,
    ReferenceBar,
    state_from_dict,
)

GENERATION_ID = "P3-R5-T2-S2"
SOURCE_SHA256 = "88bfab773f72817ee9e87228066bcaa223d62aef0fb802dd9261c1a11bce03fd"
ACTIVE_C2_AUTHORITY = "NONE"
CHECKPOINT_SCHEMA = "ovc-c2csm-reference-checkpoint/v0.1"
OUTPUT_SCHEMA = "ovc-c2csm-reference-typed-stream/v0.1"

LIFE_ACTIVE = 0
LIFE_DORMANT = 1
LIFE_RETIRED = 2

INT_REL_BELOW = -1
INT_REL_EQUAL = 0
INT_REL_ABOVE = 1
INT_REL_UNKNOWN = 2

ENV_NOT_EVALUABLE = 0
ENV_UNIQUE = 1
ENV_IDENTITY_AMBIGUOUS = 2
ENV_LIFE_ACTIVE = 0
ENV_LIFE_DORMANT_BOUNDARY = 1
ENV_LIFE_UNKNOWN = 2
ENV_REL_INSIDE = 0
ENV_REL_ABOVE = 1
ENV_REL_BELOW = -1
ENV_REL_BOUNDARY = 2
ENV_REL_UNKNOWN = 3
ENV_ROLE_NONE = 0
ENV_ROLE_CURRENT = 1

ETR_NONE = 0
ETR_BASELINE = 1
ETR_UPPER_EXPANSION = 2
ETR_LOWER_EXPANSION = 3
ETR_UPPER_CONTRACTION = 4
ETR_LOWER_CONTRACTION = 5
ETR_BOTH_EXPANSION = 6
ETR_BOTH_CONTRACTION = 7
ETR_UP_SHIFT = 8
ETR_DOWN_SHIFT = 9
ETR_IDENTITY_CHANGE_SAME_GEOMETRY = 10
ETR_EVALUABILITY_GAINED = 11
ETR_EVALUABILITY_LOST = 12
ETR_OTHER = 13

ETRC_NONE = 0
ETRC_SEQ_UP_SHIFT = 1
ETRC_SEQ_DOWN_SHIFT = 2
ETRC_COMPOUND_EXPANSION = 3
ETRC_COMPOUND_CONTRACTION = 4
ETRC_RETURN_OR_MIXED = 5
ETRC_OPEN_NO_ANCHOR = 0
ETRC_OPEN_WAIT_FIRST_MOVE = 1
ETRC_OPEN_WAIT_LOWER = 2
ETRC_OPEN_WAIT_UPPER = 3

SNAP_OFF = 0
SNAP_IN_PROGRESS = 1
SNAP_PARTIAL = 2
SNAP_COMPLETE = 3
SNAP_INTEGRITY_OPEN = 4

SLOG_TRIG_BASE = 1
SLOG_TRIG_FORM = 2
SLOG_TRIG_LIFE = 4
SLOG_TRIG_ROLE = 8
SLOG_TRIG_B_LIFE = 16
SLOG_TRIG_CMP = 32
SLOG_TRIG_OPEN = 64
SLOG_TRIG_REL = 128
SLOG_TRIG_INT = 256
SLOG_TRIG_CHK = 512
SLOG_TRIG_FINAL = 1024


class ReferenceEngineError(ValueError):
    """The exact-source reference engine cannot safely process the request."""


def _present(value: float | None) -> bool:
    return value is not None and math.isfinite(value)


def _relation(close: float, level: float) -> int:
    return INT_REL_ABOVE if close > level else INT_REL_BELOW if close < level else INT_REL_EQUAL


def _price_signature(value: float | None, mintick: float | None) -> str:
    if value is None:
        return "NA"
    if mintick is None:
        return format(value, ".15g")
    tick = Decimal(str(mintick))
    rounded = (Decimal(str(value)) / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick
    places = max(0, -tick.as_tuple().exponent)
    return f"{rounded:.{places}f}"


class C2CSMReferenceEngine:
    """Frozen P3-R5-T2-S2 historical conformance engine.

    This is a direct mechanics port of the exact-source Pine library. It is descriptive,
    reference-only, and carries no current C2 or scientific authority.
    """

    def __init__(self, state: R4State | None = None) -> None:
        self.state = state or R4State()

    def reset(self) -> None:
        self.state = R4State()

    def step(self, bar: ReferenceBar) -> R4Step:
        self._validate_bar(bar)
        if bar.enabled and bar.first_lab_bar:
            self.reset()
        r1_step = self._step_r1(bar)
        r2_step = self._step_r2(bar, r1_step)
        r3_step = self._step_r3(bar, r2_step)
        return self._step_r4(bar, r3_step)

    @staticmethod
    def _validate_bar(bar: ReferenceBar) -> None:
        if bar.segment_obs < 0:
            raise ReferenceEngineError("segment_obs must be non-negative")
        if bar.checkpoint_every < 0:
            raise ReferenceEngineError("checkpoint_every must be non-negative")
        if bar.mintick is not None and (not math.isfinite(bar.mintick) or bar.mintick <= 0):
            raise ReferenceEngineError("mintick must be positive and finite")
        for name in ("source_high", "source_low", "source_close"):
            value = getattr(bar, name)
            if value is not None and not math.isfinite(value):
                raise ReferenceEngineError(f"{name} must be finite or None")
        if bar.logic_enabled and not all(
            _present(getattr(bar, name))
            for name in ("source_high", "source_low", "source_close")
        ):
            raise ReferenceEngineError("logic_enabled requires finite HIGH/LOW/CLOSE")

    def _step_r1(self, bar: ReferenceBar) -> FormationLifecycleStep:
        r1 = self.state.r3.r2.r1
        r1.source_high_history.append(bar.source_high)
        r1.source_low_history.append(bar.source_low)
        del r1.source_high_history[:-7]
        del r1.source_low_history[:-7]

        p3_ready = (
            bar.logic_enabled
            and bar.in_lab_window
            and bar.segment_obs >= 7
            and len(r1.source_high_history) == 7
            and len(r1.source_low_history) == 7
        )
        high_candidate = r1.source_high_history[-4] if p3_ready else None
        low_candidate = r1.source_low_history[-4] if p3_ready else None
        high_event = bool(
            p3_ready
            and _present(high_candidate)
            and all(
                _present(value) and high_candidate > value  # type: ignore[operator]
                for index, value in enumerate(r1.source_high_history)
                if index != 3
            )
        )
        low_event = bool(
            p3_ready
            and _present(low_candidate)
            and all(
                _present(value) and low_candidate < value  # type: ignore[operator]
                for index, value in enumerate(r1.source_low_history)
                if index != 3
            )
        )
        result = FormationLifecycleStep(
            p3_ready=p3_ready,
            high_event=high_event,
            low_event=low_event,
            high_candidate=high_candidate,
            low_candidate=low_candidate,
        )

        if (
            bar.enabled
            and bar.logic_enabled
            and bar.in_lab_window
            and not bar.chart_gap
        ):
            close = bar.source_close
            assert close is not None
            for index, level in enumerate(r1.life_price):
                if r1.life_state[index] != LIFE_ACTIVE:
                    continue
                if bar.bar_index <= r1.life_first_valid_bar[index]:
                    continue
                beyond = close > level if r1.life_kind[index] == 1 else close < level
                if beyond:
                    r1.life_state[index] = LIFE_DORMANT
                    r1.life_dormant_bar[index] = bar.bar_index
                    r1.life_dormancy_count += 1
                    result.dormant_this_bar += 1

        if bar.enabled and high_event:
            assert high_candidate is not None
            r1.life_next_id += 1
            result.high_new_id = r1.life_next_id
            for index, old_price in enumerate(r1.life_price):
                if (
                    r1.life_state[index] == LIFE_DORMANT
                    and r1.life_kind[index] == 1
                    and high_candidate > old_price
                ):
                    r1.life_state[index] = LIFE_RETIRED
                    r1.life_retired_bar[index] = bar.bar_index
                    r1.life_retired_by_id[index] = r1.life_next_id
                    r1.life_retired_count += 1
                    result.retired_this_bar += 1
            self._append_life_object(1, high_candidate, bar.bar_index)
            r1.life_formed_count += 1
            result.formed_this_bar += 1

        if bar.enabled and low_event:
            assert low_candidate is not None
            r1.life_next_id += 1
            result.low_new_id = r1.life_next_id
            for index, old_price in enumerate(r1.life_price):
                if (
                    r1.life_state[index] == LIFE_DORMANT
                    and r1.life_kind[index] == -1
                    and low_candidate < old_price
                ):
                    r1.life_state[index] = LIFE_RETIRED
                    r1.life_retired_bar[index] = bar.bar_index
                    r1.life_retired_by_id[index] = r1.life_next_id
                    r1.life_retired_count += 1
                    result.retired_this_bar += 1
            self._append_life_object(-1, low_candidate, bar.bar_index)
            r1.life_formed_count += 1
            result.formed_this_bar += 1

        r1.life_active_now = sum(state == LIFE_ACTIVE for state in r1.life_state) if bar.enabled else 0
        r1.life_dormant_now = sum(state == LIFE_DORMANT for state in r1.life_state) if bar.enabled else 0
        r1.life_retired_now = sum(state == LIFE_RETIRED for state in r1.life_state) if bar.enabled else 0
        r1.life_max_active_count = max(r1.life_max_active_count, r1.life_active_now)
        r1.life_max_visible_count = max(
            r1.life_max_visible_count, r1.life_active_now + r1.life_dormant_now
        )
        return result

    def _append_life_object(self, kind: int, price: float, bar_index: int) -> None:
        r1 = self.state.r3.r2.r1
        r1.life_id.append(r1.life_next_id)
        r1.life_price.append(price)
        r1.life_kind.append(kind)
        r1.life_state.append(LIFE_ACTIVE)
        r1.life_first_valid_bar.append(bar_index)
        r1.life_dormant_bar.append(None)
        r1.life_retired_bar.append(None)
        r1.life_retired_by_id.append(None)

    def _step_r2(self, bar: ReferenceBar, r1_step: FormationLifecycleStep) -> R2Step:
        r2 = self.state.r3.r2
        r1 = r2.r1
        previous_contact_total = r2.int_contact_event_total
        previous_relation_total = r2.int_relation_change_event_total
        previous_revisit_total = r2.int_dormant_revisit_event_total
        old_upper_role_index = r2.env_upper_slot_index
        old_lower_role_index = r2.env_lower_slot_index

        if bar.enabled:
            assert bar.source_close is not None or not bar.logic_enabled
            while len(r2.int_last_relation) < len(r1.life_id):
                index = len(r2.int_last_relation)
                close = bar.source_close
                baseline = (
                    _relation(close, r1.life_price[index])
                    if close is not None
                    else INT_REL_UNKNOWN
                )
                r2.int_last_relation.append(baseline)
                r2.int_contact_count.append(0)
                r2.int_relation_change_count.append(0)
                r2.int_first_contact_bar.append(None)
                r2.int_last_contact_bar.append(None)
                r2.int_last_relation_change_bar.append(None)
                r2.int_dormant_revisit_count.append(0)

        if bar.enabled and bar.chart_gap:
            for index, life_state in enumerate(r1.life_state):
                if life_state != LIFE_RETIRED:
                    r2.int_last_relation[index] = INT_REL_UNKNOWN

        if bar.enabled and bar.logic_enabled and bar.in_lab_window and not bar.chart_gap:
            assert bar.source_close is not None and bar.source_low is not None and bar.source_high is not None
            for index, level in enumerate(r1.life_price):
                life_state = r1.life_state[index]
                if life_state == LIFE_RETIRED or bar.bar_index <= r1.life_first_valid_bar[index]:
                    continue
                previous = r2.int_last_relation[index]
                current = _relation(bar.source_close, level)
                if previous == INT_REL_UNKNOWN:
                    r2.int_last_relation[index] = current
                    continue
                contacted = bar.source_low <= level <= bar.source_high
                relation_changed = previous != current
                dormant_bar = r1.life_dormant_bar[index]
                was_already_dormant = (
                    life_state == LIFE_DORMANT
                    and dormant_bar is not None
                    and dormant_bar < bar.bar_index
                )
                if contacted:
                    r2.int_contact_count[index] += 1
                    r2.int_last_contact_bar[index] = bar.bar_index
                    if r2.int_first_contact_bar[index] is None:
                        r2.int_first_contact_bar[index] = bar.bar_index
                    r2.int_contact_event_total += 1
                    r2.int_event_total += 1
                if relation_changed:
                    r2.int_relation_change_count[index] += 1
                    r2.int_last_relation_change_bar[index] = bar.bar_index
                    r2.int_relation_change_event_total += 1
                    r2.int_event_total += 1
                if contacted and was_already_dormant:
                    r2.int_dormant_revisit_count[index] += 1
                    r2.int_dormant_revisit_event_total += 1
                r2.int_last_relation[index] = current

        self._refresh_interaction_counts(bar.enabled)
        self._step_roles(bar)
        interaction_changed = (
            r2.int_contact_event_total != previous_contact_total
            or r2.int_relation_change_event_total != previous_relation_total
            or r2.int_dormant_revisit_event_total != previous_revisit_total
        )
        return R2Step(
            r1=r1_step,
            env_signature_changed=r2.env_signature_changed,
            upper_role_changed=r2.env_upper_slot_index != old_upper_role_index,
            lower_role_changed=r2.env_lower_slot_index != old_lower_role_index,
            interaction_changed=interaction_changed,
        )

    def _refresh_interaction_counts(self, enabled: bool) -> None:
        r2 = self.state.r3.r2
        names = (
            "int_live_objects", "int_history_none", "int_history_contact_only",
            "int_history_relation_only", "int_history_both", "int_current_above",
            "int_current_below", "int_current_equal", "int_current_unknown",
            "int_dormant_live", "int_dormant_with_revisit",
        )
        for name in names:
            setattr(r2, name, 0)
        if not enabled:
            return
        for index, life_state in enumerate(r2.r1.life_state):
            if life_state == LIFE_RETIRED:
                continue
            r2.int_live_objects += 1
            contacts = r2.int_contact_count[index]
            relation_changes = r2.int_relation_change_count[index]
            if contacts == 0 and relation_changes == 0:
                r2.int_history_none += 1
            elif contacts > 0 and relation_changes == 0:
                r2.int_history_contact_only += 1
            elif contacts == 0 and relation_changes > 0:
                r2.int_history_relation_only += 1
            else:
                r2.int_history_both += 1
            relation_name = {
                INT_REL_ABOVE: "int_current_above",
                INT_REL_BELOW: "int_current_below",
                INT_REL_EQUAL: "int_current_equal",
            }.get(r2.int_last_relation[index], "int_current_unknown")
            setattr(r2, relation_name, getattr(r2, relation_name) + 1)
            if life_state == LIFE_DORMANT:
                r2.int_dormant_live += 1
                if r2.int_dormant_revisit_count[index] > 0:
                    r2.int_dormant_with_revisit += 1

    def _step_roles(self, bar: ReferenceBar) -> None:
        r2 = self.state.r3.r2
        r1 = r2.r1
        r2.env_active_object_count = sum(state == LIFE_ACTIVE for state in r1.life_state) if bar.enabled else 0
        r2.env_dormant_object_count = sum(state == LIFE_DORMANT for state in r1.life_state) if bar.enabled else 0
        r2.env_retired_object_count = sum(state == LIFE_RETIRED for state in r1.life_state) if bar.enabled else 0

        new_high: list[tuple[int, float]] = []
        new_low: list[tuple[int, float]] = []
        if bar.enabled and bar.in_lab_window and not bar.chart_gap:
            for index, first_valid in enumerate(r1.life_first_valid_bar):
                if first_valid != bar.bar_index or r1.life_state[index] == LIFE_RETIRED:
                    continue
                target = new_high if r1.life_kind[index] == 1 else new_low
                target.append((index, r1.life_price[index]))
        if len(new_high) > 1:
            r2.env_upper_candidate_multiplicity_count += 1
        if len(new_low) > 1:
            r2.env_lower_candidate_multiplicity_count += 1

        if self._valid_index(r2.env_pending_upper_index, r1.life_state) and r1.life_state[r2.env_pending_upper_index] == LIFE_RETIRED:  # type: ignore[index]
            r2.env_pending_upper_index = None
            r2.env_pending_upper_price = None
            r2.env_pending_upper_first_valid_bar = None
            r2.env_upper_pending_retired_count += 1
        if self._valid_index(r2.env_pending_lower_index, r1.life_state) and r1.life_state[r2.env_pending_lower_index] == LIFE_RETIRED:  # type: ignore[index]
            r2.env_pending_lower_index = None
            r2.env_pending_lower_price = None
            r2.env_pending_lower_first_valid_bar = None
            r2.env_lower_pending_retired_count += 1

        if bar.enabled and len(new_high) == 1:
            if r2.env_pending_upper_index is not None:
                r2.env_upper_pending_replaced_count += 1
            r2.env_pending_upper_index, r2.env_pending_upper_price = new_high[0]
            r2.env_pending_upper_first_valid_bar = bar.bar_index
            r2.env_upper_pending_entered_count += 1
        if bar.enabled and len(new_low) == 1:
            if r2.env_pending_lower_index is not None:
                r2.env_lower_pending_replaced_count += 1
            r2.env_pending_lower_index, r2.env_pending_lower_price = new_low[0]
            r2.env_pending_lower_first_valid_bar = bar.bar_index
            r2.env_lower_pending_entered_count += 1

        upper_had = r2.env_upper_slot_index is not None and r2.env_upper_slot_price is not None
        lower_had = r2.env_lower_slot_index is not None and r2.env_lower_slot_price is not None
        has_pending_upper = r2.env_pending_upper_index is not None and r2.env_pending_upper_price is not None
        has_pending_lower = r2.env_pending_lower_index is not None and r2.env_pending_lower_price is not None
        pair_coherent = bool(
            has_pending_upper and has_pending_lower
            and r2.env_pending_upper_price > r2.env_pending_lower_price  # type: ignore[operator]
        )
        commit_upper = bar.enabled and (
            pair_coherent
            or (has_pending_upper and (not lower_had or r2.env_pending_upper_price > r2.env_lower_slot_price))  # type: ignore[operator]
        )
        commit_lower = bar.enabled and (
            pair_coherent
            or (has_pending_lower and (not upper_had or r2.env_pending_lower_price < r2.env_upper_slot_price))  # type: ignore[operator]
        )
        if commit_upper:
            self._commit_role("upper", bar.bar_index)
        if commit_lower:
            self._commit_role("lower", bar.bar_index)

        if r2.env_pending_upper_index is not None and r2.env_pending_upper_price is not None:
            coherent = r2.env_lower_slot_price is None or r2.env_pending_upper_price > r2.env_lower_slot_price
            if bar.enabled and coherent:
                self._commit_role("upper", bar.bar_index)
        if r2.env_pending_lower_index is not None and r2.env_pending_lower_price is not None:
            coherent = r2.env_upper_slot_price is None or r2.env_pending_lower_price < r2.env_upper_slot_price
            if bar.enabled and coherent:
                self._commit_role("lower", bar.bar_index)

        if self._valid_index(r2.env_upper_slot_index, r1.life_state) and r1.life_state[r2.env_upper_slot_index] == LIFE_RETIRED:  # type: ignore[index]
            r2.env_upper_slot_index = None
            r2.env_upper_slot_price = None
            r2.env_upper_role_state = ENV_ROLE_NONE
            r2.env_upper_role_first_valid_bar = None
            r2.env_upper_role_lost_retirement_count += 1
        if self._valid_index(r2.env_lower_slot_index, r1.life_state) and r1.life_state[r2.env_lower_slot_index] == LIFE_RETIRED:  # type: ignore[index]
            r2.env_lower_slot_index = None
            r2.env_lower_slot_price = None
            r2.env_lower_role_state = ENV_ROLE_NONE
            r2.env_lower_role_first_valid_bar = None
            r2.env_lower_role_lost_retirement_count += 1

        r2.env_upper_role_valid = self._live_role(r2.env_upper_slot_index)
        r2.env_lower_role_valid = self._live_role(r2.env_lower_slot_index)
        r2.env_upper_price = r2.env_upper_slot_price if r2.env_upper_role_valid else None
        r2.env_lower_price = r2.env_lower_slot_price if r2.env_lower_role_valid else None
        r2.env_upper_unique_id = r1.life_id[r2.env_upper_slot_index] if r2.env_upper_role_valid else None  # type: ignore[index]
        r2.env_lower_unique_id = r1.life_id[r2.env_lower_slot_index] if r2.env_lower_role_valid else None  # type: ignore[index]
        r2.env_upper_boundary_dormant_count = int(
            r2.env_upper_role_valid and r1.life_state[r2.env_upper_slot_index] == LIFE_DORMANT  # type: ignore[index]
        )
        r2.env_lower_boundary_dormant_count = int(
            r2.env_lower_role_valid and r1.life_state[r2.env_lower_slot_index] == LIFE_DORMANT  # type: ignore[index]
        )
        r2.env_has_high_boundary = r2.env_upper_role_valid and r2.env_upper_price is not None
        r2.env_has_low_boundary = r2.env_lower_role_valid and r2.env_lower_price is not None
        r2.env_geometry_valid = bool(
            r2.env_has_high_boundary and r2.env_has_low_boundary
            and r2.env_upper_price > r2.env_lower_price  # type: ignore[operator]
        )
        r2.env_status = ENV_UNIQUE if r2.env_geometry_valid else ENV_NOT_EVALUABLE
        r2.env_identity_unique = r2.env_status == ENV_UNIQUE
        r2.env_lifecycle = (
            ENV_LIFE_UNKNOWN if r2.env_status == ENV_NOT_EVALUABLE
            else ENV_LIFE_DORMANT_BOUNDARY
            if r2.env_upper_boundary_dormant_count or r2.env_lower_boundary_dormant_count
            else ENV_LIFE_ACTIVE
        )
        self._refresh_envelope_population(bar.enabled)

        close = bar.source_close
        if not r2.env_geometry_valid or bar.chart_gap or close is None:
            r2.env_current_relation = ENV_REL_UNKNOWN
        elif close > r2.env_upper_price:  # type: ignore[operator]
            r2.env_current_relation = ENV_REL_ABOVE
        elif close < r2.env_lower_price:  # type: ignore[operator]
            r2.env_current_relation = ENV_REL_BELOW
        elif close == r2.env_upper_price or close == r2.env_lower_price:
            r2.env_current_relation = ENV_REL_BOUNDARY
        else:
            r2.env_current_relation = ENV_REL_INSIDE
        r2.env_width = r2.env_upper_price - r2.env_lower_price if r2.env_geometry_valid else None  # type: ignore[operator]
        r2.env_mid = (r2.env_upper_price + r2.env_lower_price) / 2.0 if r2.env_geometry_valid else None  # type: ignore[operator]

        signature = "|".join((
            str(r2.env_status),
            _price_signature(r2.env_upper_price if r2.env_geometry_valid else None, bar.mintick),
            _price_signature(r2.env_lower_price if r2.env_geometry_valid else None, bar.mintick),
            str(r2.env_upper_unique_id) if r2.env_status == ENV_UNIQUE else "NA",
            str(r2.env_lower_unique_id) if r2.env_status == ENV_UNIQUE else "NA",
        ))
        semantic_case_start = bar.enabled and bar.in_lab_window and bar.segment_obs == 1 and not bar.chart_gap
        if semantic_case_start:
            r2.env_generation = 0
            r2.env_generation_change_count = 0
            r2.env_previous_signature = ""
            r2.env_generation_first_valid_bar = None
            r2.env_signature_changed = False
        else:
            r2.env_signature_changed = bar.enabled and signature != r2.env_previous_signature
        if r2.env_signature_changed:
            r2.env_generation += 1
            if r2.env_previous_signature:
                r2.env_generation_change_count += 1
            r2.env_generation_first_valid_bar = bar.bar_index
            r2.env_previous_signature = signature

        accounted = (
            r2.env_boundary_member_count + r2.env_co_located_boundary_context_count
            + r2.env_internal_count + r2.env_outside_above_count + r2.env_outside_below_count
        )
        r2.env_object_accounting_pass = not r2.env_geometry_valid or accounted == r2.env_live_object_count

    @staticmethod
    def _valid_index(index: int | None, values: list[Any]) -> bool:
        return index is not None and 0 <= index < len(values)

    def _live_role(self, index: int | None) -> bool:
        r1 = self.state.r3.r2.r1
        return self._valid_index(index, r1.life_state) and r1.life_state[index] != LIFE_RETIRED  # type: ignore[index]

    def _commit_role(self, side: str, bar_index: int) -> None:
        r2 = self.state.r3.r2
        r1 = r2.r1
        index_name = f"env_{side}_slot_index"
        price_name = f"env_{side}_slot_price"
        pending_index_name = f"env_pending_{side}_index"
        pending_price_name = f"env_pending_{side}_price"
        old_index = getattr(r2, index_name)
        old_price = getattr(r2, price_name)
        next_index = getattr(r2, pending_index_name)
        next_price = getattr(r2, pending_price_name)
        had_boundary = old_index is not None and old_price is not None
        if had_boundary:
            setattr(r2, f"env_{side}_succession_count", getattr(r2, f"env_{side}_succession_count") + 1)
            expansion = next_price > old_price if side == "upper" else next_price < old_price
            contraction = next_price < old_price if side == "upper" else next_price > old_price
            class_name = "expansion" if expansion else "contraction" if contraction else "same_geometry"
            counter = f"env_{side}_{class_name}_succession_count"
            setattr(r2, counter, getattr(r2, counter) + 1)
            old_life = r1.life_state[old_index] if self._valid_index(old_index, r1.life_state) else LIFE_RETIRED
            if old_life == LIFE_ACTIVE:
                counter = f"env_{side}_superseded_while_active_count"
                setattr(r2, counter, getattr(r2, counter) + 1)
        else:
            counter = f"env_{side}_establishment_count"
            setattr(r2, counter, getattr(r2, counter) + 1)
        setattr(r2, index_name, next_index)
        setattr(r2, price_name, next_price)
        setattr(r2, f"env_{side}_role_state", ENV_ROLE_CURRENT)
        setattr(r2, f"env_{side}_role_first_valid_bar", bar_index)
        setattr(r2, pending_index_name, None)
        setattr(r2, pending_price_name, None)
        setattr(r2, f"env_pending_{side}_first_valid_bar", None)
        counter = f"env_{side}_pending_cleared_count"
        setattr(r2, counter, getattr(r2, counter) + 1)

    def _refresh_envelope_population(self, enabled: bool) -> None:
        r2 = self.state.r3.r2
        r1 = r2.r1
        r2.env_live_object_count = r2.env_active_object_count + r2.env_dormant_object_count
        for name in (
            "env_boundary_member_count", "env_co_located_boundary_context_count",
            "env_internal_count", "env_internal_active_count", "env_internal_dormant_count",
            "env_internal_high_count", "env_internal_low_count", "env_outside_above_count",
            "env_outside_below_count",
        ):
            setattr(r2, name, 0)
        if not enabled or not r2.env_geometry_valid:
            return
        assert r2.env_upper_price is not None and r2.env_lower_price is not None
        for index, state in enumerate(r1.life_state):
            if state == LIFE_RETIRED:
                continue
            price = r1.life_price[index]
            if index in (r2.env_upper_slot_index, r2.env_lower_slot_index):
                r2.env_boundary_member_count += 1
            elif price in (r2.env_upper_price, r2.env_lower_price):
                r2.env_co_located_boundary_context_count += 1
            elif r2.env_lower_price < price < r2.env_upper_price:
                r2.env_internal_count += 1
                if state == LIFE_ACTIVE:
                    r2.env_internal_active_count += 1
                elif state == LIFE_DORMANT:
                    r2.env_internal_dormant_count += 1
                if r1.life_kind[index] == 1:
                    r2.env_internal_high_count += 1
                elif r1.life_kind[index] == -1:
                    r2.env_internal_low_count += 1
            elif price > r2.env_upper_price:
                r2.env_outside_above_count += 1
            elif price < r2.env_lower_price:
                r2.env_outside_below_count += 1

    def _step_r3(self, bar: ReferenceBar, r2_step: R2Step) -> R3Step:
        r3 = self.state.r3
        r2 = r3.r2
        previous_resolution_count = r3.etr_compound_resolution_count
        previous_open_state = r3.etr_compound_open_state
        previous_upper_legs = r3.etr_compound_upper_leg_count
        previous_lower_legs = r3.etr_compound_lower_leg_count

        if bar.enabled and r3.etr_prev_initialised and r2.env_lifecycle != r3.etr_prev_lifecycle:
            if r3.etr_prev_lifecycle == ENV_LIFE_ACTIVE and r2.env_lifecycle == ENV_LIFE_DORMANT_BOUNDARY:
                r3.etr_dormant_boundary_entered_count += 1
            if r3.etr_prev_lifecycle == ENV_LIFE_DORMANT_BOUNDARY and r2.env_lifecycle == ENV_LIFE_ACTIVE:
                r3.etr_dormant_boundary_cleared_count += 1

        if bar.enabled and r2.env_signature_changed:
            current_evaluable = r2.env_status != ENV_NOT_EVALUABLE and r2.env_geometry_valid
            previous_evaluable = (
                r3.etr_prev_status != ENV_NOT_EVALUABLE
                and r3.etr_prev_upper is not None
                and r3.etr_prev_lower is not None
            )
            current_upper_ties = 1 if r2.env_upper_role_valid else 0
            current_lower_ties = 1 if r2.env_lower_role_valid else 0
            if not r3.etr_prev_initialised:
                r3.etr_prev_initialised = True
                r3.etr_prev_status = r2.env_status
                r3.etr_prev_upper = r2.env_upper_price if current_evaluable else None
                r3.etr_prev_lower = r2.env_lower_price if current_evaluable else None
                r3.etr_prev_upper_tie_count = current_upper_ties
                r3.etr_prev_lower_tie_count = current_lower_ties
                r3.etr_prev_upper_id = r2.env_upper_unique_id
                r3.etr_prev_lower_id = r2.env_lower_unique_id
                r3.etr_prev_lifecycle = r2.env_lifecycle
                r3.etr_latest_class = ETR_BASELINE
                r3.etr_latest_generation = r2.env_generation
                if current_evaluable:
                    self._set_compound_anchor(bar.bar_index)
            else:
                cls = self._classify_atomic(previous_evaluable, current_evaluable)
                old_width = (
                    r3.etr_prev_upper - r3.etr_prev_lower  # type: ignore[operator]
                    if previous_evaluable else None
                )
                new_width = (
                    r2.env_upper_price - r2.env_lower_price  # type: ignore[operator]
                    if current_evaluable else None
                )
                old_mid = (
                    (r3.etr_prev_upper + r3.etr_prev_lower) / 2.0  # type: ignore[operator]
                    if previous_evaluable else None
                )
                new_mid = (
                    (r2.env_upper_price + r2.env_lower_price) / 2.0  # type: ignore[operator]
                    if current_evaluable else None
                )
                width_delta = new_width - old_width if previous_evaluable and current_evaluable else None  # type: ignore[operator]
                mid_delta = new_mid - old_mid if previous_evaluable and current_evaluable else None  # type: ignore[operator]

                if r3.etr_prev_status != ENV_IDENTITY_AMBIGUOUS and r2.env_status == ENV_IDENTITY_AMBIGUOUS:
                    r3.etr_ambiguity_entered_count += 1
                if r3.etr_prev_status == ENV_IDENTITY_AMBIGUOUS and r2.env_status == ENV_UNIQUE:
                    r3.etr_ambiguity_resolved_count += 1

                r3.etr_generation_ledger.append(r2.env_generation)
                r3.etr_bar_ledger.append(bar.bar_index)
                r3.etr_class_ledger.append(cls)
                r3.etr_old_upper_ledger.append(r3.etr_prev_upper)
                r3.etr_old_lower_ledger.append(r3.etr_prev_lower)
                r3.etr_new_upper_ledger.append(r2.env_upper_price if current_evaluable else None)
                r3.etr_new_lower_ledger.append(r2.env_lower_price if current_evaluable else None)
                r3.etr_width_delta_ledger.append(width_delta)
                r3.etr_mid_delta_ledger.append(mid_delta)
                r3.etr_transition_count += 1
                self._increment_atomic_class(cls)
                r3.etr_latest_class = cls
                r3.etr_latest_generation = r2.env_generation
                r3.etr_latest_width_delta = width_delta
                r3.etr_latest_mid_delta = mid_delta
                self._advance_compound(
                    bar=bar,
                    previous_evaluable=previous_evaluable,
                    current_evaluable=current_evaluable,
                )
                r3.etr_prev_status = r2.env_status
                r3.etr_prev_upper = r2.env_upper_price if current_evaluable else None
                r3.etr_prev_lower = r2.env_lower_price if current_evaluable else None
                r3.etr_prev_upper_tie_count = current_upper_ties
                r3.etr_prev_lower_tie_count = current_lower_ties
                r3.etr_prev_upper_id = r2.env_upper_unique_id
                r3.etr_prev_lower_id = r2.env_lower_unique_id
                r3.etr_prev_lifecycle = r2.env_lifecycle

        if bar.enabled and r3.etr_prev_initialised:
            r3.etr_prev_lifecycle = r2.env_lifecycle

        if not r3.etr_compound_anchor_initialised:
            r3.etr_compound_open_state = ETRC_OPEN_NO_ANCHOR
        elif not r3.etr_compound_upper_moved and not r3.etr_compound_lower_moved:
            r3.etr_compound_open_state = ETRC_OPEN_WAIT_FIRST_MOVE
        elif r3.etr_compound_upper_moved and not r3.etr_compound_lower_moved:
            r3.etr_compound_open_state = ETRC_OPEN_WAIT_LOWER
        elif not r3.etr_compound_upper_moved and r3.etr_compound_lower_moved:
            r3.etr_compound_open_state = ETRC_OPEN_WAIT_UPPER
        else:
            r3.etr_compound_open_state = ETRC_OPEN_WAIT_FIRST_MOVE

        atomic_accounted = sum((
            r3.etr_upper_expansion_count, r3.etr_lower_expansion_count,
            r3.etr_upper_contraction_count, r3.etr_lower_contraction_count,
            r3.etr_both_expansion_count, r3.etr_both_contraction_count,
            r3.etr_up_shift_count, r3.etr_down_shift_count,
            r3.etr_identity_same_geometry_count, r3.etr_evaluability_gained_count,
            r3.etr_evaluability_lost_count, r3.etr_other_count,
        ))
        compound_accounted = sum((
            r3.etr_compound_seq_up_shift_count, r3.etr_compound_seq_down_shift_count,
            r3.etr_compound_expansion_count, r3.etr_compound_contraction_count,
            r3.etr_compound_return_mixed_count,
        ))
        r3.etr_accounting_pass = atomic_accounted == r3.etr_transition_count
        r3.etr_ledger_alignment_pass = len(r3.etr_class_ledger) == r3.etr_transition_count
        r3.etr_compound_accounting_pass = compound_accounted == r3.etr_compound_resolution_count
        r3.etr_compound_ledger_alignment_pass = (
            len(r3.etr_compound_class_ledger) == r3.etr_compound_resolution_count
        )
        compound_resolution = r3.etr_compound_resolution_count != previous_resolution_count
        return R3Step(
            r2=r2_step,
            atomic_transition=r2.env_signature_changed and r3.etr_prev_initialised,
            compound_resolution=compound_resolution,
            open_compound_changed=(
                r3.etr_compound_open_state != previous_open_state
                or r3.etr_compound_upper_leg_count != previous_upper_legs
                or r3.etr_compound_lower_leg_count != previous_lower_legs
            ),
            atomic_class=r3.etr_latest_class,
            compound_class=r3.etr_latest_compound_class if compound_resolution else ETRC_NONE,
        )

    def _classify_atomic(self, previous_evaluable: bool, current_evaluable: bool) -> int:
        r3 = self.state.r3
        r2 = r3.r2
        if not previous_evaluable and current_evaluable:
            return ETR_EVALUABILITY_GAINED
        if previous_evaluable and not current_evaluable:
            return ETR_EVALUABILITY_LOST
        if not (previous_evaluable and current_evaluable):
            return ETR_OTHER
        assert r2.env_upper_price is not None and r2.env_lower_price is not None
        assert r3.etr_prev_upper is not None and r3.etr_prev_lower is not None
        upper_same = r2.env_upper_price == r3.etr_prev_upper
        lower_same = r2.env_lower_price == r3.etr_prev_lower
        upper_up = r2.env_upper_price > r3.etr_prev_upper
        upper_down = r2.env_upper_price < r3.etr_prev_upper
        lower_up = r2.env_lower_price > r3.etr_prev_lower
        lower_down = r2.env_lower_price < r3.etr_prev_lower
        if upper_same and lower_same:
            return ETR_IDENTITY_CHANGE_SAME_GEOMETRY
        if upper_up and lower_same:
            return ETR_UPPER_EXPANSION
        if upper_same and lower_down:
            return ETR_LOWER_EXPANSION
        if upper_down and lower_same:
            return ETR_UPPER_CONTRACTION
        if upper_same and lower_up:
            return ETR_LOWER_CONTRACTION
        if upper_up and lower_down:
            return ETR_BOTH_EXPANSION
        if upper_down and lower_up:
            return ETR_BOTH_CONTRACTION
        if upper_up and lower_up:
            return ETR_UP_SHIFT
        if upper_down and lower_down:
            return ETR_DOWN_SHIFT
        return ETR_OTHER

    def _increment_atomic_class(self, cls: int) -> None:
        r3 = self.state.r3
        counter = {
            ETR_UPPER_EXPANSION: "etr_upper_expansion_count",
            ETR_LOWER_EXPANSION: "etr_lower_expansion_count",
            ETR_UPPER_CONTRACTION: "etr_upper_contraction_count",
            ETR_LOWER_CONTRACTION: "etr_lower_contraction_count",
            ETR_BOTH_EXPANSION: "etr_both_expansion_count",
            ETR_BOTH_CONTRACTION: "etr_both_contraction_count",
            ETR_UP_SHIFT: "etr_up_shift_count",
            ETR_DOWN_SHIFT: "etr_down_shift_count",
            ETR_IDENTITY_CHANGE_SAME_GEOMETRY: "etr_identity_same_geometry_count",
            ETR_EVALUABILITY_GAINED: "etr_evaluability_gained_count",
            ETR_EVALUABILITY_LOST: "etr_evaluability_lost_count",
        }.get(cls, "etr_other_count")
        setattr(r3, counter, getattr(r3, counter) + 1)

    def _clear_compound_anchor(self) -> None:
        r3 = self.state.r3
        r3.etr_compound_anchor_initialised = False
        r3.etr_compound_anchor_generation = 0
        r3.etr_compound_anchor_bar = None
        r3.etr_compound_anchor_upper = None
        r3.etr_compound_anchor_lower = None
        r3.etr_compound_upper_moved = False
        r3.etr_compound_lower_moved = False
        r3.etr_compound_upper_leg_count = 0
        r3.etr_compound_lower_leg_count = 0

    def _set_compound_anchor(self, bar_index: int) -> None:
        r3 = self.state.r3
        r2 = r3.r2
        assert r2.env_upper_price is not None and r2.env_lower_price is not None
        r3.etr_compound_anchor_initialised = True
        r3.etr_compound_anchor_generation = r2.env_generation
        r3.etr_compound_anchor_bar = bar_index
        r3.etr_compound_anchor_upper = r2.env_upper_price
        r3.etr_compound_anchor_lower = r2.env_lower_price
        r3.etr_compound_upper_moved = False
        r3.etr_compound_lower_moved = False
        r3.etr_compound_upper_leg_count = 0
        r3.etr_compound_lower_leg_count = 0

    def _advance_compound(
        self, *, bar: ReferenceBar, previous_evaluable: bool, current_evaluable: bool
    ) -> None:
        r3 = self.state.r3
        r2 = r3.r2
        if previous_evaluable and not current_evaluable:
            if r3.etr_compound_anchor_initialised and (
                r3.etr_compound_upper_moved or r3.etr_compound_lower_moved
            ):
                r3.etr_compound_reset_on_evaluability_loss_count += 1
            self._clear_compound_anchor()
            return
        if not previous_evaluable and current_evaluable:
            self._set_compound_anchor(bar.bar_index)
            return
        if not (previous_evaluable and current_evaluable):
            return
        if not r3.etr_compound_anchor_initialised:
            self._set_compound_anchor(bar.bar_index)
            return
        assert r2.env_upper_price is not None and r2.env_lower_price is not None
        assert r3.etr_prev_upper is not None and r3.etr_prev_lower is not None
        if r2.env_upper_price != r3.etr_prev_upper:
            r3.etr_compound_upper_moved = True
            r3.etr_compound_upper_leg_count += 1
        if r2.env_lower_price != r3.etr_prev_lower:
            r3.etr_compound_lower_moved = True
            r3.etr_compound_lower_leg_count += 1
        if not (r3.etr_compound_upper_moved and r3.etr_compound_lower_moved):
            return
        assert r3.etr_compound_anchor_upper is not None and r3.etr_compound_anchor_lower is not None
        upper_above = r2.env_upper_price > r3.etr_compound_anchor_upper
        upper_below = r2.env_upper_price < r3.etr_compound_anchor_upper
        lower_above = r2.env_lower_price > r3.etr_compound_anchor_lower
        lower_below = r2.env_lower_price < r3.etr_compound_anchor_lower
        if upper_above and lower_above:
            cls = ETRC_SEQ_UP_SHIFT
        elif upper_below and lower_below:
            cls = ETRC_SEQ_DOWN_SHIFT
        elif upper_above and lower_below:
            cls = ETRC_COMPOUND_EXPANSION
        elif upper_below and lower_above:
            cls = ETRC_COMPOUND_CONTRACTION
        else:
            cls = ETRC_RETURN_OR_MIXED
        anchor_width = r3.etr_compound_anchor_upper - r3.etr_compound_anchor_lower
        final_width = r2.env_upper_price - r2.env_lower_price
        anchor_mid = (r3.etr_compound_anchor_upper + r3.etr_compound_anchor_lower) / 2.0
        final_mid = (r2.env_upper_price + r2.env_lower_price) / 2.0
        width_delta = final_width - anchor_width
        mid_delta = final_mid - anchor_mid
        r3.etr_compound_anchor_generation_ledger.append(r3.etr_compound_anchor_generation)
        r3.etr_compound_resolution_generation_ledger.append(r2.env_generation)
        r3.etr_compound_resolution_bar_ledger.append(bar.bar_index)
        r3.etr_compound_class_ledger.append(cls)
        r3.etr_compound_anchor_upper_ledger.append(r3.etr_compound_anchor_upper)
        r3.etr_compound_anchor_lower_ledger.append(r3.etr_compound_anchor_lower)
        r3.etr_compound_final_upper_ledger.append(r2.env_upper_price)
        r3.etr_compound_final_lower_ledger.append(r2.env_lower_price)
        r3.etr_compound_width_delta_ledger.append(width_delta)
        r3.etr_compound_mid_delta_ledger.append(mid_delta)
        r3.etr_compound_upper_leg_count_ledger.append(r3.etr_compound_upper_leg_count)
        r3.etr_compound_lower_leg_count_ledger.append(r3.etr_compound_lower_leg_count)
        r3.etr_compound_resolution_count += 1
        counter = {
            ETRC_SEQ_UP_SHIFT: "etr_compound_seq_up_shift_count",
            ETRC_SEQ_DOWN_SHIFT: "etr_compound_seq_down_shift_count",
            ETRC_COMPOUND_EXPANSION: "etr_compound_expansion_count",
            ETRC_COMPOUND_CONTRACTION: "etr_compound_contraction_count",
        }.get(cls, "etr_compound_return_mixed_count")
        setattr(r3, counter, getattr(r3, counter) + 1)
        r3.etr_latest_compound_class = cls
        r3.etr_latest_compound_anchor_generation = r3.etr_compound_anchor_generation
        r3.etr_latest_compound_resolution_generation = r2.env_generation
        r3.etr_latest_compound_width_delta = width_delta
        r3.etr_latest_compound_mid_delta = mid_delta
        r3.etr_latest_compound_upper_legs = r3.etr_compound_upper_leg_count
        r3.etr_latest_compound_lower_legs = r3.etr_compound_lower_leg_count
        self._set_compound_anchor(bar.bar_index)

    def _step_r4(self, bar: ReferenceBar, r3_step: R3Step) -> R4Step:
        r4 = self.state
        r3 = r4.r3
        r2 = r3.r2
        r1 = r2.r1
        life_total = r1.life_active_now + r1.life_dormant_now + r1.life_retired_now
        interaction_history_total = (
            r2.int_history_none + r2.int_history_contact_only
            + r2.int_history_relation_only + r2.int_history_both
        )
        interaction_relation_total = (
            r2.int_current_above + r2.int_current_below
            + r2.int_current_equal + r2.int_current_unknown
        )
        r4.snap_integrity_pass = all((
            life_total == r1.life_formed_count,
            interaction_history_total == r2.int_live_objects,
            interaction_relation_total == r2.int_live_objects,
            r2.int_live_objects == r1.life_active_now + r1.life_dormant_now,
            len(r2.int_last_relation) == len(r1.life_id),
            r2.env_object_accounting_pass,
            r3.etr_accounting_pass,
            r3.etr_ledger_alignment_pass,
            r3.etr_compound_accounting_pass,
            r3.etr_compound_ledger_alignment_pass,
        ))
        r4.snap_measurements_complete = (
            bar.in_lab_window and bar.segment_obs >= 4
            and bar.segment_obs >= 8 and bar.segment_obs >= 16
        )
        r4.snap_status = SNAP_OFF
        if bar.enabled and bar.in_lab_window:
            if not r4.snap_integrity_pass:
                r4.snap_status = SNAP_INTEGRITY_OPEN
            elif not bar.window_complete:
                r4.snap_status = SNAP_IN_PROGRESS
            elif r4.snap_measurements_complete:
                r4.snap_status = SNAP_COMPLETE
            else:
                r4.snap_status = SNAP_PARTIAL
        r4.snap_sequence = bar.sequence if bar.in_lab_window else 0
        r4.snap_cutoff_ms = bar.cutoff_ms if bar.in_lab_window else None
        r4.snap_live_object_count = r1.life_active_now + r1.life_dormant_now
        r4.snap_active_count = r1.life_active_now
        r4.snap_dormant_count = r1.life_dormant_now
        r4.snap_retired_count = r1.life_retired_now
        r4.snap_latest_compound_class = r3.etr_latest_compound_class
        r4.snap_compound_open_state = r3.etr_compound_open_state
        r4.snap_compound_anchor_generation = (
            r3.etr_compound_anchor_generation if r3.etr_compound_anchor_initialised else 0
        )
        r4.snap_compound_anchor_upper = (
            r3.etr_compound_anchor_upper if r3.etr_compound_anchor_initialised else None
        )
        r4.snap_compound_anchor_lower = (
            r3.etr_compound_anchor_lower if r3.etr_compound_anchor_initialised else None
        )
        r4.snap_compound_upper_legs = r3.etr_compound_upper_leg_count
        r4.snap_compound_lower_legs = r3.etr_compound_lower_leg_count

        flags = self._succession_flags(bar)
        append_now = bar.enabled and bar.in_lab_window and any(flags.values())
        appended_id = 0
        trigger_mask = 0
        trigger_text = ""
        if append_now:
            trigger_parts: list[str] = []
            trigger_spec = (
                ("baseline", "BASE", SLOG_TRIG_BASE, "slog_baseline_record_count"),
                ("form", "FORM", SLOG_TRIG_FORM, "slog_form_trigger_count"),
                ("life", "LIFE", SLOG_TRIG_LIFE, "slog_life_trigger_count"),
                ("role", "ROLE", SLOG_TRIG_ROLE, "slog_role_trigger_count"),
                ("boundary_life", "B-LIFE", SLOG_TRIG_B_LIFE, "slog_boundary_life_trigger_count"),
                ("compound", "CMP", SLOG_TRIG_CMP, "slog_compound_trigger_count"),
                ("open", "OPEN", SLOG_TRIG_OPEN, "slog_open_trigger_count"),
                ("relation", "REL", SLOG_TRIG_REL, "slog_relation_only_trigger_count"),
                ("interaction", "INT", SLOG_TRIG_INT, "slog_interaction_only_trigger_count"),
                ("checkpoint", "CHK", SLOG_TRIG_CHK, "slog_checkpoint_trigger_count"),
                ("final", "FINAL", SLOG_TRIG_FINAL, "slog_final_trigger_count"),
            )
            for flag_name, code, mask, counter in trigger_spec:
                if flags[flag_name]:
                    trigger_parts.append(code)
                    trigger_mask += mask
                    setattr(r4, counter, getattr(r4, counter) + 1)
            if flags["final"]:
                r4.slog_final_recorded = True
            trigger_text = "+".join(trigger_parts)
            appended_id = len(r4.slog_record_id) + 1
            self._append_succession_record(bar, appended_id, trigger_text, trigger_mask)

        if bar.enabled and bar.in_lab_window:
            r4.slog_prev_initialised = True
            r4.slog_prev_formed = r1.life_formed_count
            r4.slog_prev_active = r1.life_active_now
            r4.slog_prev_dormant = r1.life_dormant_now
            r4.slog_prev_retired = r1.life_retired_now
            r4.slog_prev_env_generation = r2.env_generation
            r4.slog_prev_env_lifecycle = r2.env_lifecycle
            r4.slog_prev_env_relation = r2.env_current_relation
            r4.slog_prev_compound_resolution_count = r3.etr_compound_resolution_count
            r4.slog_prev_compound_open_state = r3.etr_compound_open_state
            r4.slog_prev_compound_upper_legs = r3.etr_compound_upper_leg_count
            r4.slog_prev_compound_lower_legs = r3.etr_compound_lower_leg_count
            r4.slog_prev_contact_total = r2.int_contact_event_total
            r4.slog_prev_relation_change_total = r2.int_relation_change_event_total
            r4.slog_prev_dormant_revisit_total = r2.int_dormant_revisit_event_total
            r4.slog_prev_int_above = r2.int_current_above
            r4.slog_prev_int_below = r2.int_current_below
            r4.slog_prev_int_equal = r2.int_current_equal
            r4.slog_prev_int_unknown = r2.int_current_unknown
        r4.slog_record_count = len(r4.slog_record_id)
        if r4.slog_record_count:
            index = r4.slog_record_count - 1
            r4.slog_latest_record_id = r4.slog_record_id[index]
            r4.slog_latest_sequence = r4.slog_sequence[index]
            r4.slog_latest_env_generation = r4.slog_env_generation[index]
            r4.slog_latest_atomic_class = r4.slog_atomic_class[index]
            r4.slog_latest_compound_class = r4.slog_compound_class[index]
            r4.slog_latest_open_state = r4.slog_compound_open_state[index]
            r4.slog_latest_integrity = r4.slog_integrity_pass[index]
        return R4Step(
            r3=r3_step,
            record_appended=append_now,
            record_id=appended_id,
            trigger_mask=trigger_mask,
            trigger_text=trigger_text,
            final_recorded=r4.slog_final_recorded,
        )

    def _succession_flags(self, bar: ReferenceBar) -> dict[str, bool]:
        r4 = self.state
        r3 = r4.r3
        r2 = r3.r2
        r1 = r2.r1
        initialised = bar.enabled and bar.in_lab_window and r4.slog_prev_initialised
        form = initialised and r1.life_formed_count != r4.slog_prev_formed
        life = initialised and (
            r1.life_active_now != r4.slog_prev_active
            or r1.life_dormant_now != r4.slog_prev_dormant
            or r1.life_retired_now != r4.slog_prev_retired
        )
        role = initialised and r2.env_generation != r4.slog_prev_env_generation
        boundary_life = initialised and r2.env_lifecycle != r4.slog_prev_env_lifecycle
        compound = initialised and r3.etr_compound_resolution_count != r4.slog_prev_compound_resolution_count
        open_changed = initialised and (
            r3.etr_compound_open_state != r4.slog_prev_compound_open_state
            or r3.etr_compound_upper_leg_count != r4.slog_prev_compound_upper_legs
            or r3.etr_compound_lower_leg_count != r4.slog_prev_compound_lower_legs
        )
        relation_changed = initialised and r2.env_current_relation != r4.slog_prev_env_relation
        interaction_changed = initialised and (
            r2.int_contact_event_total != r4.slog_prev_contact_total
            or r2.int_relation_change_event_total != r4.slog_prev_relation_change_total
            or r2.int_dormant_revisit_event_total != r4.slog_prev_dormant_revisit_total
            or r2.int_current_above != r4.slog_prev_int_above
            or r2.int_current_below != r4.slog_prev_int_below
            or r2.int_current_equal != r4.slog_prev_int_equal
            or r2.int_current_unknown != r4.slog_prev_int_unknown
        )
        checkpoint = initialised and bar.checkpoint_every > 0 and bar.sequence > 0 and bar.sequence % bar.checkpoint_every == 0
        final = initialised and bar.window_complete and not r4.slog_final_recorded
        baseline = (
            bar.enabled and bar.in_lab_window and not r4.slog_prev_initialised
            and (r1.life_formed_count > 0 or r2.env_generation > 0)
        )
        return {
            "baseline": baseline,
            "form": form,
            "life": life,
            "role": role,
            "boundary_life": boundary_life,
            "compound": compound,
            "open": open_changed,
            "relation": bar.record_relation_only and relation_changed,
            "interaction": bar.record_interaction_only and interaction_changed,
            "checkpoint": checkpoint,
            "final": final,
        }

    def _append_succession_record(
        self, bar: ReferenceBar, record_id: int, trigger: str, trigger_mask: int
    ) -> None:
        r4 = self.state
        r3 = r4.r3
        r2 = r3.r2
        r1 = r2.r1
        values: tuple[tuple[str, Any], ...] = (
            ("slog_record_id", record_id), ("slog_sequence", bar.sequence),
            ("slog_cutoff_ms", bar.cutoff_ms), ("slog_trigger", trigger),
            ("slog_trigger_mask", trigger_mask), ("slog_formed", r1.life_formed_count),
            ("slog_active", r1.life_active_now), ("slog_dormant", r1.life_dormant_now),
            ("slog_retired", r1.life_retired_now), ("slog_env_generation", r2.env_generation),
            ("slog_upper_id", r2.env_upper_unique_id if r2.env_has_high_boundary else None),
            ("slog_lower_id", r2.env_lower_unique_id if r2.env_has_low_boundary else None),
            ("slog_upper_price", r2.env_upper_price if r2.env_geometry_valid else None),
            ("slog_lower_price", r2.env_lower_price if r2.env_geometry_valid else None),
            ("slog_width", r2.env_width if r2.env_geometry_valid else None),
            ("slog_env_relation", r2.env_current_relation),
            ("slog_env_lifecycle", r2.env_lifecycle), ("slog_internal_count", r2.env_internal_count),
            ("slog_outside_count", r2.env_outside_above_count + r2.env_outside_below_count),
            ("slog_atomic_class", r3.etr_latest_class),
            ("slog_compound_class", r3.etr_latest_compound_class),
            ("slog_compound_anchor_generation", r3.etr_compound_anchor_generation if r3.etr_compound_anchor_initialised else 0),
            ("slog_compound_open_state", r3.etr_compound_open_state),
            ("slog_compound_upper_legs", r3.etr_compound_upper_leg_count),
            ("slog_compound_lower_legs", r3.etr_compound_lower_leg_count),
            ("slog_contact_total", r2.int_contact_event_total),
            ("slog_relation_change_total", r2.int_relation_change_event_total),
            ("slog_dormant_revisit_total", r2.int_dormant_revisit_event_total),
            ("slog_snapshot_status", r4.snap_status),
            ("slog_integrity_pass", 1 if r4.snap_integrity_pass else 0),
        )
        for name, value in values:
            getattr(r4, name).append(value)

    def checkpoint(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": CHECKPOINT_SCHEMA,
            "generation_id": GENERATION_ID,
            "source_sha256": SOURCE_SHA256,
            "active_c2_authority": ACTIVE_C2_AUTHORITY,
            "state": asdict(self.state),
        }
        payload["checkpoint_id"] = canonical_sha256(payload)
        return payload

    def checkpoint_bytes(self) -> bytes:
        return canonical_json_bytes(self.checkpoint())

    @classmethod
    def from_checkpoint(cls, checkpoint: Mapping[str, Any] | bytes | str) -> "C2CSMReferenceEngine":
        if isinstance(checkpoint, bytes):
            payload = json.loads(checkpoint.decode("utf-8"))
        elif isinstance(checkpoint, str):
            payload = json.loads(checkpoint)
        else:
            payload = dict(checkpoint)
        expected_id = payload.pop("checkpoint_id", None)
        if expected_id != canonical_sha256(payload):
            raise ReferenceEngineError("checkpoint identity mismatch")
        if payload.get("schema") != CHECKPOINT_SCHEMA:
            raise ReferenceEngineError("checkpoint schema mismatch")
        if payload.get("generation_id") != GENERATION_ID or payload.get("source_sha256") != SOURCE_SHA256:
            raise ReferenceEngineError("checkpoint source binding mismatch")
        if payload.get("active_c2_authority") != ACTIVE_C2_AUTHORITY:
            raise ReferenceEngineError("checkpoint authority boundary mismatch")
        state = payload.get("state")
        if not isinstance(state, dict):
            raise ReferenceEngineError("checkpoint state missing")
        return cls(state_from_dict(state))

    def typed_output(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": OUTPUT_SCHEMA,
            "generation_id": GENERATION_ID,
            "source_sha256": SOURCE_SHA256,
            "role": "DESCRIPTIVE_REFERENCE_CONFORMANCE_ONLY",
            "active_c2_authority": ACTIVE_C2_AUTHORITY,
            "state": asdict(self.state),
        }
        payload["output_id"] = canonical_sha256(payload)
        return payload

    def typed_output_bytes(self) -> bytes:
        return canonical_json_bytes(self.typed_output())

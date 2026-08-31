from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ReferenceBar:
    enabled: bool
    logic_enabled: bool
    in_lab_window: bool
    first_lab_bar: bool
    chart_gap: bool
    segment_obs: int
    bar_index: int
    source_high: float | None
    source_low: float | None
    source_close: float | None
    sequence: int
    cutoff_ms: int | None
    mintick: float | None = None
    window_complete: bool = False
    checkpoint_every: int = 0
    record_relation_only: bool = False
    record_interaction_only: bool = False


@dataclass(slots=True)
class FormationLifecycleStep:
    p3_ready: bool = False
    high_event: bool = False
    low_event: bool = False
    high_candidate: float | None = None
    low_candidate: float | None = None
    formed_this_bar: int = 0
    dormant_this_bar: int = 0
    retired_this_bar: int = 0
    high_new_id: int = 0
    low_new_id: int = 0


@dataclass(slots=True)
class R2Step:
    r1: FormationLifecycleStep = field(default_factory=FormationLifecycleStep)
    env_signature_changed: bool = False
    upper_role_changed: bool = False
    lower_role_changed: bool = False
    interaction_changed: bool = False


@dataclass(slots=True)
class R3Step:
    r2: R2Step = field(default_factory=R2Step)
    atomic_transition: bool = False
    compound_resolution: bool = False
    open_compound_changed: bool = False
    atomic_class: int = 0
    compound_class: int = 0


@dataclass(slots=True)
class R4Step:
    r3: R3Step = field(default_factory=R3Step)
    record_appended: bool = False
    record_id: int = 0
    trigger_mask: int = 0
    trigger_text: str = ""
    final_recorded: bool = False


@dataclass(slots=True)
class R1State:
    life_next_id: int = 0
    life_id: list[int] = field(default_factory=list)
    life_price: list[float] = field(default_factory=list)
    life_kind: list[int] = field(default_factory=list)
    life_state: list[int] = field(default_factory=list)
    life_first_valid_bar: list[int] = field(default_factory=list)
    life_dormant_bar: list[int | None] = field(default_factory=list)
    life_retired_bar: list[int | None] = field(default_factory=list)
    life_retired_by_id: list[int | None] = field(default_factory=list)
    life_formed_count: int = 0
    life_dormancy_count: int = 0
    life_retired_count: int = 0
    life_active_now: int = 0
    life_dormant_now: int = 0
    life_retired_now: int = 0
    life_max_active_count: int = 0
    life_max_visible_count: int = 0
    source_high_history: list[float | None] = field(default_factory=list)
    source_low_history: list[float | None] = field(default_factory=list)


@dataclass(slots=True)
class R2State:
    r1: R1State = field(default_factory=R1State)
    int_last_relation: list[int] = field(default_factory=list)
    int_contact_count: list[int] = field(default_factory=list)
    int_relation_change_count: list[int] = field(default_factory=list)
    int_first_contact_bar: list[int | None] = field(default_factory=list)
    int_last_contact_bar: list[int | None] = field(default_factory=list)
    int_last_relation_change_bar: list[int | None] = field(default_factory=list)
    int_dormant_revisit_count: list[int] = field(default_factory=list)
    int_contact_event_total: int = 0
    int_relation_change_event_total: int = 0
    int_dormant_revisit_event_total: int = 0
    int_event_total: int = 0
    int_live_objects: int = 0
    int_history_none: int = 0
    int_history_contact_only: int = 0
    int_history_relation_only: int = 0
    int_history_both: int = 0
    int_current_above: int = 0
    int_current_below: int = 0
    int_current_equal: int = 0
    int_current_unknown: int = 0
    int_dormant_live: int = 0
    int_dormant_with_revisit: int = 0
    env_upper_slot_index: int | None = None
    env_lower_slot_index: int | None = None
    env_upper_slot_price: float | None = None
    env_lower_slot_price: float | None = None
    env_upper_role_state: int = 0
    env_lower_role_state: int = 0
    env_upper_role_first_valid_bar: int | None = None
    env_lower_role_first_valid_bar: int | None = None
    env_pending_upper_index: int | None = None
    env_pending_lower_index: int | None = None
    env_pending_upper_price: float | None = None
    env_pending_lower_price: float | None = None
    env_pending_upper_first_valid_bar: int | None = None
    env_pending_lower_first_valid_bar: int | None = None
    env_upper_establishment_count: int = 0
    env_lower_establishment_count: int = 0
    env_upper_succession_count: int = 0
    env_lower_succession_count: int = 0
    env_upper_expansion_succession_count: int = 0
    env_upper_contraction_succession_count: int = 0
    env_upper_same_geometry_succession_count: int = 0
    env_lower_expansion_succession_count: int = 0
    env_lower_contraction_succession_count: int = 0
    env_lower_same_geometry_succession_count: int = 0
    env_upper_superseded_while_active_count: int = 0
    env_lower_superseded_while_active_count: int = 0
    env_upper_pending_entered_count: int = 0
    env_lower_pending_entered_count: int = 0
    env_upper_pending_cleared_count: int = 0
    env_lower_pending_cleared_count: int = 0
    env_upper_pending_replaced_count: int = 0
    env_lower_pending_replaced_count: int = 0
    env_upper_pending_retired_count: int = 0
    env_lower_pending_retired_count: int = 0
    env_upper_candidate_multiplicity_count: int = 0
    env_lower_candidate_multiplicity_count: int = 0
    env_upper_role_lost_retirement_count: int = 0
    env_lower_role_lost_retirement_count: int = 0
    env_active_object_count: int = 0
    env_dormant_object_count: int = 0
    env_retired_object_count: int = 0
    env_live_object_count: int = 0
    env_boundary_member_count: int = 0
    env_co_located_boundary_context_count: int = 0
    env_internal_count: int = 0
    env_internal_active_count: int = 0
    env_internal_dormant_count: int = 0
    env_internal_high_count: int = 0
    env_internal_low_count: int = 0
    env_outside_above_count: int = 0
    env_outside_below_count: int = 0
    env_upper_role_valid: bool = False
    env_lower_role_valid: bool = False
    env_upper_price: float | None = None
    env_lower_price: float | None = None
    env_upper_unique_id: int | None = None
    env_lower_unique_id: int | None = None
    env_upper_boundary_dormant_count: int = 0
    env_lower_boundary_dormant_count: int = 0
    env_has_high_boundary: bool = False
    env_has_low_boundary: bool = False
    env_geometry_valid: bool = False
    env_status: int = 0
    env_identity_unique: bool = False
    env_lifecycle: int = 2
    env_current_relation: int = 3
    env_width: float | None = None
    env_mid: float | None = None
    env_generation: int = 0
    env_generation_change_count: int = 0
    env_previous_signature: str = ""
    env_generation_first_valid_bar: int | None = None
    env_signature_changed: bool = False
    env_object_accounting_pass: bool = True


@dataclass(slots=True)
class R3State:
    r2: R2State = field(default_factory=R2State)
    etr_prev_initialised: bool = False
    etr_prev_status: int = 0
    etr_prev_upper: float | None = None
    etr_prev_lower: float | None = None
    etr_prev_upper_tie_count: int = 0
    etr_prev_lower_tie_count: int = 0
    etr_prev_upper_id: int | None = None
    etr_prev_lower_id: int | None = None
    etr_prev_lifecycle: int = 0
    etr_generation_ledger: list[int] = field(default_factory=list)
    etr_bar_ledger: list[int] = field(default_factory=list)
    etr_class_ledger: list[int] = field(default_factory=list)
    etr_old_upper_ledger: list[float | None] = field(default_factory=list)
    etr_old_lower_ledger: list[float | None] = field(default_factory=list)
    etr_new_upper_ledger: list[float | None] = field(default_factory=list)
    etr_new_lower_ledger: list[float | None] = field(default_factory=list)
    etr_width_delta_ledger: list[float | None] = field(default_factory=list)
    etr_mid_delta_ledger: list[float | None] = field(default_factory=list)
    etr_transition_count: int = 0
    etr_upper_expansion_count: int = 0
    etr_lower_expansion_count: int = 0
    etr_upper_contraction_count: int = 0
    etr_lower_contraction_count: int = 0
    etr_both_expansion_count: int = 0
    etr_both_contraction_count: int = 0
    etr_up_shift_count: int = 0
    etr_down_shift_count: int = 0
    etr_identity_same_geometry_count: int = 0
    etr_evaluability_gained_count: int = 0
    etr_evaluability_lost_count: int = 0
    etr_other_count: int = 0
    etr_ambiguity_entered_count: int = 0
    etr_ambiguity_resolved_count: int = 0
    etr_dormant_boundary_entered_count: int = 0
    etr_dormant_boundary_cleared_count: int = 0
    etr_latest_class: int = 0
    etr_latest_generation: int = 0
    etr_latest_width_delta: float | None = None
    etr_latest_mid_delta: float | None = None
    etr_compound_anchor_initialised: bool = False
    etr_compound_anchor_generation: int = 0
    etr_compound_anchor_bar: int | None = None
    etr_compound_anchor_upper: float | None = None
    etr_compound_anchor_lower: float | None = None
    etr_compound_upper_moved: bool = False
    etr_compound_lower_moved: bool = False
    etr_compound_upper_leg_count: int = 0
    etr_compound_lower_leg_count: int = 0
    etr_compound_resolution_count: int = 0
    etr_compound_seq_up_shift_count: int = 0
    etr_compound_seq_down_shift_count: int = 0
    etr_compound_expansion_count: int = 0
    etr_compound_contraction_count: int = 0
    etr_compound_return_mixed_count: int = 0
    etr_compound_reset_on_evaluability_loss_count: int = 0
    etr_latest_compound_class: int = 0
    etr_latest_compound_anchor_generation: int = 0
    etr_latest_compound_resolution_generation: int = 0
    etr_latest_compound_width_delta: float | None = None
    etr_latest_compound_mid_delta: float | None = None
    etr_latest_compound_upper_legs: int = 0
    etr_latest_compound_lower_legs: int = 0
    etr_compound_anchor_generation_ledger: list[int] = field(default_factory=list)
    etr_compound_resolution_generation_ledger: list[int] = field(default_factory=list)
    etr_compound_resolution_bar_ledger: list[int] = field(default_factory=list)
    etr_compound_class_ledger: list[int] = field(default_factory=list)
    etr_compound_anchor_upper_ledger: list[float] = field(default_factory=list)
    etr_compound_anchor_lower_ledger: list[float] = field(default_factory=list)
    etr_compound_final_upper_ledger: list[float] = field(default_factory=list)
    etr_compound_final_lower_ledger: list[float] = field(default_factory=list)
    etr_compound_width_delta_ledger: list[float] = field(default_factory=list)
    etr_compound_mid_delta_ledger: list[float] = field(default_factory=list)
    etr_compound_upper_leg_count_ledger: list[int] = field(default_factory=list)
    etr_compound_lower_leg_count_ledger: list[int] = field(default_factory=list)
    etr_compound_open_state: int = 0
    etr_accounting_pass: bool = True
    etr_ledger_alignment_pass: bool = True
    etr_compound_accounting_pass: bool = True
    etr_compound_ledger_alignment_pass: bool = True


@dataclass(slots=True)
class R4State:
    r3: R3State = field(default_factory=R3State)
    snap_status: int = 0
    snap_sequence: int = 0
    snap_cutoff_ms: int | None = None
    snap_integrity_pass: bool = True
    snap_measurements_complete: bool = False
    snap_live_object_count: int = 0
    snap_active_count: int = 0
    snap_dormant_count: int = 0
    snap_retired_count: int = 0
    snap_latest_compound_class: int = 0
    snap_compound_open_state: int = 0
    snap_compound_anchor_generation: int = 0
    snap_compound_anchor_upper: float | None = None
    snap_compound_anchor_lower: float | None = None
    snap_compound_upper_legs: int = 0
    snap_compound_lower_legs: int = 0
    slog_record_id: list[int] = field(default_factory=list)
    slog_sequence: list[int] = field(default_factory=list)
    slog_cutoff_ms: list[int | None] = field(default_factory=list)
    slog_trigger: list[str] = field(default_factory=list)
    slog_trigger_mask: list[int] = field(default_factory=list)
    slog_formed: list[int] = field(default_factory=list)
    slog_active: list[int] = field(default_factory=list)
    slog_dormant: list[int] = field(default_factory=list)
    slog_retired: list[int] = field(default_factory=list)
    slog_env_generation: list[int] = field(default_factory=list)
    slog_upper_id: list[int | None] = field(default_factory=list)
    slog_lower_id: list[int | None] = field(default_factory=list)
    slog_upper_price: list[float | None] = field(default_factory=list)
    slog_lower_price: list[float | None] = field(default_factory=list)
    slog_width: list[float | None] = field(default_factory=list)
    slog_env_relation: list[int] = field(default_factory=list)
    slog_env_lifecycle: list[int] = field(default_factory=list)
    slog_internal_count: list[int] = field(default_factory=list)
    slog_outside_count: list[int] = field(default_factory=list)
    slog_atomic_class: list[int] = field(default_factory=list)
    slog_compound_class: list[int] = field(default_factory=list)
    slog_compound_anchor_generation: list[int] = field(default_factory=list)
    slog_compound_open_state: list[int] = field(default_factory=list)
    slog_compound_upper_legs: list[int] = field(default_factory=list)
    slog_compound_lower_legs: list[int] = field(default_factory=list)
    slog_contact_total: list[int] = field(default_factory=list)
    slog_relation_change_total: list[int] = field(default_factory=list)
    slog_dormant_revisit_total: list[int] = field(default_factory=list)
    slog_snapshot_status: list[int] = field(default_factory=list)
    slog_integrity_pass: list[int] = field(default_factory=list)
    slog_prev_initialised: bool = False
    slog_prev_formed: int = 0
    slog_prev_active: int = 0
    slog_prev_dormant: int = 0
    slog_prev_retired: int = 0
    slog_prev_env_generation: int = 0
    slog_prev_env_lifecycle: int = 2
    slog_prev_env_relation: int = 3
    slog_prev_compound_resolution_count: int = 0
    slog_prev_compound_open_state: int = 0
    slog_prev_compound_upper_legs: int = 0
    slog_prev_compound_lower_legs: int = 0
    slog_prev_contact_total: int = 0
    slog_prev_relation_change_total: int = 0
    slog_prev_dormant_revisit_total: int = 0
    slog_prev_int_above: int = 0
    slog_prev_int_below: int = 0
    slog_prev_int_equal: int = 0
    slog_prev_int_unknown: int = 0
    slog_final_recorded: bool = False
    slog_baseline_record_count: int = 0
    slog_form_trigger_count: int = 0
    slog_life_trigger_count: int = 0
    slog_role_trigger_count: int = 0
    slog_boundary_life_trigger_count: int = 0
    slog_compound_trigger_count: int = 0
    slog_open_trigger_count: int = 0
    slog_relation_only_trigger_count: int = 0
    slog_interaction_only_trigger_count: int = 0
    slog_checkpoint_trigger_count: int = 0
    slog_final_trigger_count: int = 0
    slog_record_count: int = 0
    slog_latest_record_id: int = 0
    slog_latest_sequence: int = 0
    slog_latest_env_generation: int = 0
    slog_latest_atomic_class: int = 0
    slog_latest_compound_class: int = 0
    slog_latest_open_state: int = 0
    slog_latest_integrity: int = 0


def state_from_dict(payload: dict[str, Any]) -> R4State:
    r4_payload = dict(payload)
    r3_payload = dict(r4_payload.pop("r3"))
    r2_payload = dict(r3_payload.pop("r2"))
    r1_payload = dict(r2_payload.pop("r1"))
    r1 = R1State(**r1_payload)
    r2 = R2State(r1=r1, **r2_payload)
    r3 = R3State(r2=r2, **r3_payload)
    return R4State(r3=r3, **r4_payload)

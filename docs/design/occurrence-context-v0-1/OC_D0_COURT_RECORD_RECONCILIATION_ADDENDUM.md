# OC-D0 — Latest-Main Court-Record Reconciliation Addendum

**Design:** `OVC-OCCURRENCE-CONTEXT-DESIGN-SPEC-0.1`  
**Gate:** `OC-D0`  
**Original inspected baseline:** `main@549b09e6a6e98366db12a07e57bb2d0991c3b6f6`  
**Latest lawful main reconciled before operator decision:** `main@6f895f07a1c3eb61f532dd2daf92c7ca6b8099b6`  
**Final operator-decision reconciliation commit:** `56413d64244a8ed6bddd06f1e67f954aafc681fe`  
**Authority effect:** `NONE`

## Purpose

Main advanced twice while OC-D0 was being materialized. This addendum is the controlling court-record reconciliation for Section 0.2 of the long-form design specification and any earlier gate-packet wording. It changes no OccurrenceContext design semantics.

## Exact successor state

The two intervening C2E main commits were:

1. `a35543c0845f1af70d896a449bd9739af753b8f4` — record operator `C2E2-G6-RUN-AUTH DEFER`.
2. `6f895f07a1c3eb61f532dd2daf92c7ca6b8099b6` — seal the terminal C2E2-G6 DEFER merge receipt/state.

The authoritative C2E current-state pointer at the OC-D0 operator decision records:

- `authoritative_state = registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_16.json`
- `current_gate = C2E2-G6-RUN-AUTH`
- `status = BLOCKED`
- `operator_decision = DEFER`
- `operator_decision_required = false`
- `real_source_replay = DENIED_DEFERRED_AT_C2E2_G6`
- `wp6_execution = DENIED`
- `active_c2e = NONE`
- `active_boundary_pack = NONE`
- `next_action = FUTURE_APPEND_ONLY_G6_SUPERSESSION_AFTER_EXACT_PREREQUISITES`

Therefore any earlier wording that says C2E2-G6 is `GATE_READY`, that PR #444 is open, or that `a35543c...` is the latest main is superseded by this addendum.

## Design consequence

None of the OccurrenceContext design contracts require revision:

1. OccurrenceContext binds to the frozen typed C2E v0.2 object/schema contract without presuming real-source activation.
2. Episode-relative context remains unavailable for any source occurrence that lacks a lawful C2E episode object.
3. Exact ID/hash/FVT anchor proof remains mandatory; legacy or synthetic evidence cannot substitute for a missing lawful source occurrence.
4. C2E real-source execution, WP6 and activation remain outside OC authority.
5. C2P remains not started.
6. The OC-D0 PASS grants design acceptance only and permits preparation of the separate OccurrenceContext implementation plan.

The branch contains latest lawful main through a non-destructive merge reconciliation; no force-push or history rewrite was used.

## Gate disposition

`OC-D0 = PASS / OPERATOR` recorded in `OC_D0_OPERATOR_DECISION.json`.

Implementation authority remains `NONE_PENDING_OC_G0`.

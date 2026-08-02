# OVC MTA C2 Translation Audit Contract v0.1

**Programme:** `OVC-MTA-v0.2`  
**Packet:** `MTA-WP3`  
**Gate:** `MTA-G3`  
**Authority:** audit-only; no model, selector, release, clock, threshold, C2E, C2.5, C3, Validation or exposure authority.

## Purpose

Audit the frozen June C2 translation produced by `PD-JUNE-FM.RUN.9810cfa8a2e2930be2e503b9`. The audit reconstructs the currently implemented level, container, relation, axis, persistence, transition and reset behaviour without changing it.

## Frozen inputs

The checksum-addressed input set contains:

- four C1 streams: 15M and 2H_A_L, BID and ASK;
- six C2 state streams: 15M local, 15M with first-valid 2H parent, and 2H local, each by side;
- six matching C2 transition streams;
- the two complete/incomplete 2H bar ledgers required to reproduce parent-level availability events.

The authoritative path, size, SHA-256 and record count for each file is recorded in `MTA_WP3_C2_TRANSLATION_AUDIT_REFERENCE.json`. Raw streams remain outside Git.

## Required reconstruction

Every accepted C2 state ID must reconstruct from the exact C1 record, active parameter pack, evaluation scope, lawful history and first-valid parent-level event. Reconstruction includes:

- `RANGE_HIGH`, `RANGE_LOW`, `MIDPOINT`, `SWING_HIGH` and `SWING_LOW`;
- `LOCAL_RANGE`, `PARENT_RANGE` and `SWING_ENVELOPE` containers, including explicit exclusions and conflicts;
- the complete relation inventory and relation-set ID, with no hidden winning-level selection;
- all five independent axes: LOCATION, MOTION, ORGANISATION, INTERACTION and QUALITY;
- persistence counters and continuity resets;
- parent-event emptying on incomplete 2H buckets and first-valid re-entry after a complete parent bucket.

Every accepted C2 transition ID must reconstruct from its exact from/to state IDs, first-valid time and exact changed-axis set. A transition is not accepted when the state vector is unchanged.

## Accounting invariants

The frozen audit denominator is:

- 9,420 C2 states, of which 8,598 are June target states;
- 7,345 C2 transitions, of which 6,783 are June target transitions;
- 16,765 accepted state/transition IDs reconstructed;
- zero unaccounted C2 records and zero state, level, container, relation, axis, persistence, transition or annotation mismatches.

## Required findings

The audit must preserve findings even when exact translation passes:

1. `QUALITY_NEVER_COMPLETE`: target QUALITY is 3,602 CENSORED plus 4,996 DEGRADED, with zero COMPLETE states.
2. `PARENT_RANGE_NEVER_ACTIVE`: `PARENT_RANGE` is excluded for all 8,598 target state evaluations under the current contiguous 24-bar parent-range requirement.
3. `THREE_AXES_NOT_EVALUATED`: LOCATION, MOTION and ORGANISATION are each NOT_EVALUATED for 3,602 target states because `LOCAL_RANGE` warm-up is incomplete after resets.
4. `EXACT_TRANSLATION`: all accepted C2 identities and computations reproduce exactly.

These findings do not change formulas, thresholds, clocks or semantics. They are evidence for later audit packets and operator decisions only.

## Gate rule

MTA-G3 passes only when:

- all 18 external inputs match the frozen manifest by SHA-256 and byte size;
- every accepted state and transition ID reconstructs exactly;
- every structural object and exclusion is accounted for;
- all five axes, persistence counters, transitions and reset/warm-up behaviour match exactly;
- mismatch and unaccounted counts are zero;
- required repository, focused and final-head checks pass;
- QA recommends `PASS_WITH_MATERIAL_FINDINGS`;
- no operator-reserved authority delta occurs.

A passing MTA-G3 is auto-ratifiable because it accepts audit evidence only. Automatic continuation then stops at `MTA-A3`. MTA-A3 is an operator acknowledgement of the material structural findings and a decision to continue, defer, block or quarantine before MTA-WP4 begins.

## Capacity and rollback

The external audit is compact and below the four-hour/10GB packet bounds. Rollback is non-destructive: supersede the audit through a new immutable version bound to exact input hashes, while preserving the source streams, external audit, findings, QA, decision and acknowledgement history.

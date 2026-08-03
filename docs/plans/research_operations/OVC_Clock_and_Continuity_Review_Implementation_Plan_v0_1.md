# OVC Clock and Continuity Review Implementation Plan v0.1

## 1. Identity and authority

- **Programme ID:** `OVC-CLOCK-CONTINUITY-REVIEW-v0.1`
- **Plan ID:** `OVC-CLOCK-CONTINUITY-REVIEW-IMPLEMENTATION-PLAN-0.1`
- **Source authority:** `MTA-G8-CLOCK=PASS`
- **Source decision:** `MTA-G8.OPERATOR.MULTIPART.20260803T114000+0100`
- **Initial gate:** `CCR-G0`
- **Current status:** `GATE_READY`
- **Authority available now:** preparation of this plan and its gate packet only
- **Authority denied now:** any clock, continuity, reset, formula, threshold, selector, release, provider, Validation, publication, probability, risk, exposure or execution change

`CCR-G0` is operator-required. Nothing after `CCR-00` may execute until the operator approves the frozen review contract and shadow variants.

## 2. Purpose

Determine whether the current fixed `2H_A_L` UTC measurement clock and strict continuity/reset rules are accurately translating the available GBPUSD market record, or whether they are causing avoidable censoring, repeated warm-up, low parent-context usability and systematic loss of higher-timeframe structure.

This programme does not assume that the existing clock is wrong. It separates four questions:

1. Is the current clock implemented exactly as contracted?
2. Are resets correctly classified as provider gaps, planned market closures, malformed continuity or genuine unavailable evidence?
3. How much C2 computability and parent usability is lost after each reset and why?
4. Would a separately governed continuity interpretation improve evidence availability without interpolation, leakage or semantic distortion?

The fixed clock remains the authoritative baseline throughout this review.

## 3. Binding baseline findings

The review inherits the following accepted MTA findings:

- the `2H_A_L` mapping is exact and no future parent is consumed;
- unknown reset count is zero in the audited slice;
- provider-gap resets were observed 48 times per side;
- parent level context was usable for 615 of 4,072 target resolutions, or `15.103143%`;
- `PARENT_RANGE` was active in zero target states;
- LOCATION, MOTION and ORGANISATION were not evaluated in 3,602 target states because local-range warm-up was incomplete after resets;
- no current finding authorises a clock or continuity change.

These findings are inputs, not conclusions about the preferred future clock.

## 4. Scope

### 4.1 Included

- GBPUSD only;
- existing M1, 15M and `2H_A_L` BID/ASK records already admitted by the June full-month source boundary;
- exact reconstruction of current clock membership, close times, first-valid times and parent resolution;
- reset and discontinuity classification;
- rolling warm-up and computability-loss accounting;
- shadow-only comparison of the three variants frozen at `CCR-G0`;
- read-only evidence, QA, decision packets and rollback records.

### 4.2 Excluded

- adding an instrument, market, side, provider or undeclared dependency;
- changing the authoritative `2H_A_L` clock;
- activating an alternative clock or continuity rule;
- interpolation, gap filling, synthetic bars or forward information;
- formula or threshold changes in C1 or C2;
- selector replacement, release publication or Validation consumption;
- market meaning, probability, risk, exposure, trading or execution.

## 5. Frozen review variants

`CCR-G0` must freeze exactly three continuity variants. They are analytical variants, not active contracts.

### V0 — CURRENT_STRICT_CONTINUITY

The current authoritative rule. A discontinuity exists whenever the prior close is not exactly equal to the next open under the existing contract. History resets and the complete rolling warm-up restarts.

### V1 — PLANNED_CLOSURE_CLASSIFIED_CONTINUITY

A shadow interpretation that classifies declared market-closure intervals separately from unexplained provider discontinuities. It may preserve a continuity lineage flag across a planned closure only for analysis. It may not create missing bars, interpolate values or alter first-valid timestamps.

### V2 — PROVIDER_GAP_SEGMENTED_CONTINUITY

A shadow interpretation that keeps strict resets but partitions each reset by evidence-backed cause and duration, allowing computability loss to be attributed to provider gaps, source-boundary effects, planned closures or malformed adjacency. It does not preserve rolling history across any gap.

Only V0 is authoritative. V1 and V2 are evidence-producing shadows. Sensitivity results cannot override V0 without a later operator decision and a new immutable contract.

## 6. Performance and artifact contract

For each work packet:

- expected local runtime: no more than 4 hours;
- external artifact size: no more than 10GB;
- deterministic checkpoints at least every 30 minutes for long scans;
- no raw market data committed to Git;
- all external artifacts require physical SHA-256, logical SHA-256, byte size, source manifest and reproduction command.

If a bound is exceeded, the packet records `CAPACITY_EXCEEDED`, preserves completed partitions and checkpoints, writes a blocker packet and stops without weakening acceptance.

## 7. Work packets

### CCR-00 — Review contract and gate freeze

Deliver:

- clock/continuity review contract;
- reset-cause taxonomy;
- three frozen variants;
- metric registry;
- artifact and runtime bounds;
- programme state and `CCR-G0` packet.

**Gate `CCR-G0`: OPERATOR_REQUIRED.**

Acceptance requires exact authority boundaries, no active clock delta, no interpolation path and an explicit rollback.

### CCR-WP1 — Current-clock reconstruction audit

Reconstruct every relevant M1→15M→2H membership and verify:

- bar membership and close boundaries;
- completed-parent-only selection;
- first-valid timestamps;
- A–L bucket identity;
- BID/ASK population accounting;
- zero future-parent usage;
- reset locations and source evidence.

Outputs are deterministic audit tables and mismatch ledgers. Any unexplained mismatch blocks continuation.

### CCR-WP2 — Reset and warm-up census

For every reset, report:

- cause classification;
- elapsed gap duration;
- side and clock;
- source boundary proximity;
- minutes and parent bars until each C2 axis becomes evaluable;
- states censored during warm-up;
- parent level availability and parent age;
- contribution to `PARENT_RANGE` exclusion.

Primary measures include window-level, axis-level, parent-resolution and reset-episode denominators.

### CCR-WP3 — Three-variant shadow comparison

Run V0, V1 and V2 over the same pinned source identities. Report:

- exact state and transition accounting;
- axis computability changes;
- parent usability changes;
- active/excluded container counts;
- changed first-valid identities;
- any leakage or non-reproducibility;
- sensitivity by week, side, A–L block and reset cause.

V1 and V2 outputs are `SHADOW_ONLY`, `NON_CANONICAL` and `NON_PROMOTABLE`.

### CCR-WP4 — Translation consequence review

Assess how the current continuity rule affects downstream evidence without assigning market meaning:

- C2E episode segmentation feasibility;
- C2.5 event computability;
- 2H parent context availability;
- overlap and independence calculations;
- RO4 sequence evidence comparability.

Contradictions with MTA or RO4 are recorded as explicit cross-programme incidents.

### CCR-WP5 — Recommendation and final gate

Produce one decomposable recommendation covering:

- retain current rule unchanged;
- amend continuity classification only;
- design a new clock/continuity contract;
- quarantine one or more shadow variants;
- collect additional source evidence before deciding.

**Gate `CCR-G5`: OPERATOR_REQUIRED.** A PASS may authorise a later implementation plan only. It may not activate a clock or continuity change directly.

## 8. Metrics

Minimum metrics:

- exact clock-membership mismatch count;
- reset count and duration by cause;
- warm-up bars and wall-clock duration after reset;
- axis-level not-evaluable rate;
- full-vector usability rate;
- parent usability rate;
- `PARENT_RANGE` active/excluded counts;
- changed identity count under each shadow;
- post-reset transition loss;
- sensitivity across V0/V1/V2;
- runtime, checkpoint count and artifact size.

No aggregate rate may be reported without its numerator, denominator and population identity.

## 9. QA and gates

Each packet requires:

- deterministic rerun equality;
- schema validation;
- source-hash verification;
- focused tests;
- complete repository suite on the final head;
- QA recommendation of PASS or PASS_WITH_MATERIAL_FINDINGS;
- zero unresolved review threads;
- explicit authority-delta check.

Auto-ratification is allowed only for non-reserved audit packets after `CCR-G0`. Any proposed clock or continuity authority remains operator-reserved.

## 10. Stop conditions

Stop immediately for:

- any attempt to activate V1 or V2;
- a new clock, market, side, provider or dependency;
- interpolation or synthetic gap repair;
- material change to a frozen C1/C2 contract;
- non-reproducible source or artifact;
- unexplained identity mismatch;
- runtime or storage capacity exceeded without lawful partitioning;
- formula, threshold, selector, Validation, publication, risk or execution authority.

## 11. Rollback

All outputs are append-only evidence and replaceable derived shadows. Rollback means disabling or superseding the derived review route, preserving source manifests, hashes, QA, decisions and negative findings. No accepted evidence is deleted and no history is rewritten.

## 12. Work after `CCR-G0` approval

Create the frozen contracts and registries, implement deterministic read-only auditors, run the current-clock reconstruction, produce the reset/warm-up census, execute the three shadow variants, complete QA and stop at `CCR-G5` for the operator’s decomposed decision.

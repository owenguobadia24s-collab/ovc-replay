# OVC Clock and Continuity Review Contract v0.1

## Authority

This contract is active under `CCR-G0.OPERATOR.PASS.20260803T125100+0100` for read-only audit and shadow comparison only. The existing `2H_A_L` UTC clock and strict continuity rule remain authoritative.

## Frozen variants

- `V0_CURRENT_STRICT_CONTINUITY_AUTHORITATIVE`: current reset rule; every contracted discontinuity restarts history.
- `V1_PLANNED_CLOSURE_CLASSIFIED_CONTINUITY_SHADOW_ONLY`: planned closures are classified separately and may preserve an analytical lineage flag only; no bars, values or first-valid timestamps are created.
- `V2_PROVIDER_GAP_SEGMENTED_CONTINUITY_SHADOW_ONLY`: strict resets remain, with deterministic cause and duration attribution.

No fourth variant or parameter search is lawful.

## Reset taxonomy

`SOURCE_PARTITION_START`, `SCHEDULED_MARKET_CLOSURE`, `PROVIDER_GAP`, `MALFORMED_ADJACENCY`, `UNKNOWN_DISCONTINUITY`. Unknown or ambiguous evidence fails closed.

## Metrics

Every rate records numerator, denominator and population identity. Required measures include exact clock-membership mismatches, reset counts/durations by cause, post-reset warm-up bars and time, axis not-evaluable rates, full-vector and parent usability, `PARENT_RANGE` availability, changed identities under shadows, transition loss, runtime, checkpoint and artifact sizes.

## Capacity

One packet attempt is bounded to 14,400 seconds and 10,737,418,240 retained bytes. Long scans checkpoint at least every 30 minutes. `CAPACITY_EXCEEDED` preserves completed shards and stops without sampling or weakening acceptance.

## Denials

No interpolation, synthetic bars, source repair, clock or continuity activation, C1/C2 formula or threshold change, selector/release mutation, Validation, publication, semantic, probability, risk, exposure or execution authority.

## Final boundary

`CCR-G5` is operator-required before any later implementation plan. A recommendation never changes the active clock directly.

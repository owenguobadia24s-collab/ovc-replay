# Pattern Discovery Scale, Controls and Backpressure Contract v0.2

## Input-rate model

For each instrument and price side:

- 15M: 4 evaluations/hour.
- 2H: 0.5 evaluations/hour.
- Base: 4.5 evaluations/hour.
- BID + ASK: 9 evaluations/hour, or 216 evaluations/day.

The runtime must multiply this base by instrument, side, clock and independently evaluated scope counts and publish the expected volume in health metadata.

## Initial performance objectives

- New C2 record indexed within 5 seconds of availability.
- Trigger evaluation complete within 10 seconds.
- Review-queue projection updated within 15 seconds.
- Exact operational cluster rebuild within 5 minutes.

A missed objective creates a named degradation state; it does not alter chronology or discard records.

## Hard limits

- Maximum open candidate per trigger family/instrument/clock/side/scope: 1.
- Maximum simultaneously open windows per instrument: 20.
- Maximum queue promotions per instrument per eligible UTC day: 12.
- Maximum promotions from one trigger family per day: 3.
- Maximum unresolved review-queue depth per instrument: 50.
- Queue item becomes `STALE` after 5 eligible operating days.
- Operational clustering maximum: 500 active candidates per structural partition or 180 eligible trading days, whichever bound is reached first.
- Incident and lineage-failure items bypass ranking caps but remain subject to storage and UI safety controls.

## Deterministic deduplication

`candidate_dedup_key` is the canonical serialization of:

`instrument | price_side | clock | evaluation_scope | primary_trigger_family | parent_container_id | boundary_or_relation_id | open_window_epoch`

All TriggerEvents are persisted. Compatible events attach to an existing open window. Incompatible closure profiles create separate windows subject to caps.

## Overload sequence

1. Persist every TriggerEvent.
2. Group exact equivalents by deduplication key.
3. Attach compatible triggers to open candidates.
4. Enforce per-family and total open-window caps.
5. Rank closed candidates for queue promotion.
6. Reserve the required control representation.
7. Persist overflow with an exact `SUPPRESSED_*` reason.

No event or candidate is silently deleted.

## Control sampling

Cluster-eligible controls must comprise at least 20% of the analytical population.

- At least 50% of controls are `MATCHED_CONTROL`.
- At least 25% are `POPULATION_CONTROL`.
- The remainder is declared by a versioned control-sampling pack.

Matched controls align with the triggered population on instrument, side, clock, scope, parent-container class and broad structural regime. Exceptions require a reason code. All controls require the same lineage and quality admissibility as triggered candidates. Only a deterministic subset must enter human review.

## Capacity block

If a partition exceeds 500 active candidates or exact PAM exceeds five minutes:

- retain the previous immutable ClusterVersion;
- emit `CLUSTER_BUILD_CAPACITY_BLOCK`;
- freeze cluster-normalized novelty;
- continue raw distance and non-cluster review where lawful;
- open an operator capacity decision.

No approximate clustering fallback is automatic.

## Degradation escalation

| State | Immediate action | Escalation | Permitted operation |
|---|---|---|---|
| `DEGRADED_INDEX_LATENCY` | Show warning and record metric | Incident after 3 consecutive late cycles | Historical read remains; pause current candidate creation if backlog exceeds one source interval |
| `DEGRADED_TRIGGER_LATENCY` | Throttle queue projection | Stop new window opening if chronology cannot be preserved | Persist input and resume only after deterministic catch-up |
| `STALE_QUEUE_PROJECTION` | Show represented timestamp | Disable current-window review after threshold | Closed historical candidates remain readable |
| `CLUSTER_BUILD_TIMEOUT` | Keep prior cluster version | Incident after 2 consecutive failures | Disable cluster-normalized novelty |
| `EVIDENCE_SERVICE_UNAVAILABLE` | Disable freeze action | Incident after reconciliation timeout | Read and draft only |
| `AUDIT_CHAIN_FAILURE` | Fail append transaction | Immediate BLOCK | No evidence write |
| `SOURCE_SELECTOR_CHANGED` | Stop prospective job | Require explicit rebind gate | Historical review only |
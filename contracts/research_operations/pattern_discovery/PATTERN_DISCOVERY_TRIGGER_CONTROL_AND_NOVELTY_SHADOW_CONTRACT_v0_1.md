# Pattern Discovery Trigger, Control and Novelty-Shadow Contract v0.1

## Packet and authority

This contract governs `PD-WP2` under the approved `PD-G1` transition and CandidateWindow foundation.

The packet may:

- evaluate the frozen non-outcome trigger registry deterministically;
- produce reason-coded TriggerEvents from exact first-valid C2 transitions;
- select deterministic matched and population controls;
- calculate queue backpressure and promotion projections;
- calculate baseline-forming and calibrated-shadow novelty metadata;
- emit derived metrics, fixtures, QA and review packets.

The packet may not activate a live Pattern Discovery job, change the active C2 selector, enable active novelty ranking, create cluster authority, append canonical evidence, consume Validation, use OPT-C/OPT-D outcomes, or create C2E, C2.5, C3, probability, exposure, trading, execution or agent-write authority.

## Frozen trigger evaluation

The implementation must recognise the trigger IDs and closure profiles in `PATTERN_DISCOVERY_TRIGGER_REGISTRY_v0_1.yaml`. A trigger result records:

- trigger ID and registry version;
- family and exact reason code;
- first-valid UTC time;
- source TransitionRecord IDs;
- closure-profile ID and rate-limit group;
- evaluation result: `FIRED`, `NOT_FIRED` or `NOT_EVALUABLE`;
- explicit not-evaluable reason where applicable.

The evaluator may use only current and prior admissible C2 states, exact transition records and declared bounded history. A missing parent, gap, mixed binding, unknown value or insufficient history produces `NOT_EVALUABLE`; it never becomes false or neutral silently.

`TR-NOV-001`, `TR-NOV-002` and `TR-REC-001` remain non-promoting in PD-WP2. They may be represented only as descriptive shadow assessments where their required fingerprint or cluster parents exist. They cannot independently open or promote a candidate.

## Trigger predicates admitted in PD-WP2

- `TR-LOC-001`: first transition into a registered boundary-zone location value.
- `TR-INT-001`: first transition into a registered breach-active interaction value.
- `TR-INT-002`: first return-inside transition after an admissible breach-active state.
- `TR-ORG-001`: first compression-to-displacement transition pair.
- `TR-XSC-001`: first declared local/parent directional conflict.
- `TR-XSC-002`: first declared alignment after an admissible conflict.
- `TR-PER-001`: first closed bar reaching a versioned consecutive-state duration.
- `TR-INS-001`: first closed bar reaching a versioned switching count inside a bounded lookback.
- `TR-CTL-001`: deterministic control selection under a frozen sampling pack.

All categorical value sets, duration thresholds, lookbacks and tie-breaking rules are versioned. No UI or runtime default may alter them.

## Deterministic controls

Two control classes are required:

- `MATCHED_CONTROL`: same instrument, side, clock, scope, parent-container class and broad structural regime as a triggered case, but the target trigger did not fire.
- `POPULATION_CONTROL`: deterministic sample from the complete eligible C2 population without target-case matching.

Selection identity binds the control-pack version, seed, source C2 identity, source release, clock, side and scope. Repeated selection from identical inputs produces identical results.

For every cluster-eligible analytical population:

- controls are at least 20%;
- at least 50% of controls are matched controls;
- at least 25% are population controls;
- deficits are explicit metrics, not silently repaired by relabelling triggered cases.

Only a deterministic subset is promoted for human review.

## Backpressure and queue projection

The implementation enforces the frozen contract:

- maximum 12 promotions per instrument per eligible UTC day;
- maximum 3 promotions from one trigger family per day;
- maximum unresolved queue depth 50;
- incidents and lineage failures bypass ranking caps but not the hard queue-depth safety limit;
- every suppressed candidate remains retained with an exact `SUPPRESSED_*` reason;
- control slots are reserved before ordinary candidate ranking.

Ordering is deterministic by authority priority, trigger family, first-valid time and candidate ID. No opaque interest score is used.

## Novelty states

### BASELINE_FORMING

The implementation may show:

- prior signature count and eligible frequency;
- raw nearest-neighbour distance over the admitted provisional token representation;
- elapsed eligible time and count since last occurrence;
- explicit baseline sufficiency counters.

It must show no LOW/MEDIUM/HIGH badge, contribute zero queue-ranking weight and independently promote no candidate.

Minimum readiness for `CALIBRATED_SHADOW` is 60 completed valid candidates, 12 valid controls, 10 eligible operating days, more than one declared market condition and no unresolved critical lineage or leakage incident.

### CALIBRATED_SHADOW

After an explicit calibration transition record, the implementation may show percentile bands marked `SHADOW` and hypothetical rank impact. Actual queue order and promotion remain unchanged. At least 20 further shadow-evaluated candidates and disagreement metrics are required before any later activation proposal.

### ACTIVE_NOVELTY_RANKING

Prohibited in PD-WP2. Any attempt to activate it fails closed with `OPERATOR_GATE_REQUIRED`.

## Novelty representation

Before PD-WP3 fingerprints and clusters exist, distance is an explicitly provisional Jaccard distance over a canonical token set containing transition grammar, parent context and closure class. This representation is not a PatternFingerprint and cannot create cluster or archetype authority.

No return, MFE, MAE, profitable direction, horizon, outcome, setup, trade or execution field is permitted.

## Degradation metrics

The packet emits named states for index latency over 5 seconds, trigger latency over 10 seconds and queue projection over 15 seconds. Degradation changes health and permitted operation only; it never alters chronology, drops records or changes a trigger result.

## PD-G2 acceptance

`PD-G2` may pass only if:

1. every supported frozen trigger has positive, negative and not-evaluable fixtures;
2. all fired triggers retain exact source and first-valid lineage;
3. novelty and recurrence triggers cannot promote candidates;
4. control selection and control requirements are deterministic;
5. queue caps, family caps, control reservation and suppression reasons are reproducible;
6. baseline-forming novelty has no badge or ranking effect;
7. active novelty activation fails closed;
8. performance/degradation states are explicit;
9. no prohibited downstream field or dependency is present;
10. focused, retained-boundary and canonical repository tests pass.

## Rollback

Delete and rebuild derived trigger evaluations, control selections, novelty-shadow assessments, queue projections and metrics. Preserve contracts, fixtures, QA, decisions and accepted PD-WP1 records. No canonical C2 record, selector, release, evidence record or R2 object is changed.

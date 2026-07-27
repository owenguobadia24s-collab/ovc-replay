# PD-WP2 — Trigger, Control and Novelty-Shadow Engine

## Status

`QA_REVIEW_PD_G2`

## Governing plan

- Plan: `OVC C2 Pattern Discovery and Review Layer v0.3`
- Source SHA-256: `03a4c602026950f3a496f6bf2085c378a62292090d334f3b0ea2f17f6463a0aa`
- Approved prerequisite: `PD-G1 PASS`
- Baseline main commit: `abc0f4dc63932907c331f645b17ec4cdd3bb58cf`
- Branch: `build/pd-wp2-trigger-control-novelty`
- Pull request: `#93`

## Implemented capability

- deterministic evaluation of the frozen structural-transition trigger families;
- explicit positive, negative and `NOT_EVALUABLE` trigger results;
- cross-scale conflict and alignment evaluation with parent-context denial;
- first-crossing persistence and repeated-switching triggers under versioned thresholds;
- exact source TransitionRecord and first-valid lineage;
- deterministic population-control and matched-control selection;
- control-representation requirement and deficit reporting;
- deterministic queue projection with daily, family and unresolved-depth caps;
- control-slot reservation and explicit `SUPPRESSED_*` records;
- incident-first ordering without bypassing hard UI depth safety;
- provisional signature identity and Jaccard nearest-neighbour distance;
- `BASELINE_FORMING` readiness counters;
- `CALIBRATED_SHADOW` badges and hypothetical rank impact with zero actual ranking weight;
- fail-closed denial of `ACTIVE_NOVELTY_RANKING`;
- explicit latency and degradation-state projection;
- focused fixtures, tests and dedicated GitHub Actions workflow.

## Authority boundary

The packet creates replaceable derived trigger evaluations, control selections, queue projections and novelty-shadow assessments. It does not activate a live Pattern Discovery job, active novelty ranking, recurrence promotion, fingerprints, clustering, evidence writes, selectors, releases, R2, C2E, C2.5, C3, Validation, probability, exposure, trading, execution or agent authority.

## Trigger scope

Operational trigger predicates implemented in this packet:

- `TR-LOC-001 — BOUNDARY_ZONE_ENTRY`
- `TR-INT-001 — BREACH_ACTIVE`
- `TR-INT-002 — RETURN_INSIDE`
- `TR-ORG-001 — COMPRESSION_TO_DISPLACEMENT`
- `TR-XSC-001 — LOCAL_PARENT_CONFLICT`
- `TR-XSC-002 — ALIGNMENT_GAINED`
- `TR-PER-001 — LONG_PERSISTENCE`
- `TR-INS-001 — REPEATED_SWITCHING`
- `TR-CTL-001 — DETERMINISTIC_STABLE_SAMPLE`

`TR-NOV-001`, `TR-NOV-002` and `TR-REC-001` remain non-promoting because PD-WP3 fingerprint and cluster parents do not yet exist.

## Controls

The implementation preserves the two frozen control classes:

- `MATCHED_CONTROL`: exact instrument, side, clock, scope, parent-container class and broad regime match where the target trigger did not fire;
- `POPULATION_CONTROL`: deterministic sample from the complete eligible stream.

The analytical population requirement remains at least 20% controls, at least 50% matched and at least 25% population controls. Deficits remain explicit rather than being silently repaired.

## Novelty authority

During `BASELINE_FORMING`, the system exposes prior signature count, eligible frequency, raw nearest-neighbour distance and readiness counters. It exposes no novelty badge and uses zero queue-ranking weight.

During `CALIBRATED_SHADOW`, it may show `SHADOW_LOW`, `SHADOW_MEDIUM`, `SHADOW_HIGH` or `SHADOW_UNAVAILABLE` and a hypothetical rank impact, while actual order and promotion remain unchanged.

Any attempt to activate novelty ranking raises `OPERATOR_GATE_REQUIRED`.

## Persistence and storage

All outputs remain derived and replaceable. Full operational streams stay outside Git. This packet adds only compact contracts, code, fixtures, tests, QA, gate and decision records.

## Corrected defect

The first queue fixture expected all twelve available daily slots to fill even though the input contained only three eligible trigger families and the frozen three-per-family cap allowed ten total promotions. The fixture was corrected to assert the lawful bounded result rather than weaken the family cap.

## Rollback

Delete and rebuild derived trigger, control, novelty-shadow and queue-projection artifacts from accepted PD-WP1 and C2 sources. No canonical C2 record, selector, release, evidence record or R2 object changes.

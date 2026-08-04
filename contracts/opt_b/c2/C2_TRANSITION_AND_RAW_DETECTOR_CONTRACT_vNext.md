# C2 Transition Classification and Raw Detector Contract vNext

## Authority

This contract is effective only as `SHADOW_FROZEN_READ_ONLY` under `CEAR-G7.OPERATOR.PASS.20260804T234400+0100`. It does not activate a detector, select a canonical detector, choose a threshold, create a semantic interaction label, promote an event or episode, resolve parent context, publish a release, consume Validation, or grant probability, risk, exposure or execution authority.

## Transition classes

A deterministic comparison returns every applicable class and one primary class under this evidence-severity order:

1. `STRUCTURAL_CHANGE`
2. `REFERENCE_IDENTITY_CHANGE`
3. `COMPUTABILITY_CHANGE`
4. `CATEGORICAL_CHANGE`
5. `MEASUREMENT_CHANGE`
6. `NO_CHANGE`

The primary class is an indexing convenience and carries no market meaning. Comparisons require the same profile version, the same declared scope and strictly ordered observation times. Future, outcome, probability, risk, trading and execution fields are prohibited.

## Raw detectors

The frozen detector IDs are:

- `C2.DETECTOR.FIXED_OBJECT_CROSSING.v1`
- `C2.DETECTOR.PRECISION_TOUCH.v1`
- `C2.DETECTOR.CONTAINER_ENTRY_EXIT.v1`
- `C2.DETECTOR.RAW_DISTANCE_CHANGE.v1`
- `C2.DETECTOR.REFERENCE_IDENTITY_CHANGE.v1`
- `C2.DETECTOR.STRUCTURAL_GRAPH_CHANGE.v1`

All outputs are inactive, noncanonical, threshold-free and semantically neutral. Multiple raw outputs may coexist and no detector has precedence.

### Crossing

Directional crossing requires one unchanged immutable object identity and a strictly ordered M1 or tick path. Values are compared only at declared source precision. OHLC span has no directional path-order authority. A reference-identity change is never crossing.

### Touch

Touch is exact equality at declared source precision. Proximity is not a substitute.

### Container entry and exit

Entry or exit requires two chronological point relations against the same immutable positive-width container. Boundary-only observations do not imply acceptance or rejection.

### Distance

Distance change reports only increased, decreased or unchanged absolute distance against the same immutable object. It cannot emit approach, test or retreat semantics.

### Structural graph

Structural comparison requires complete previous and current node and edge inventories. Added nodes, explicit supersessions, edge additions/removals and structural-depth changes are raw facts only.

## Fail-closed rules

Missing, ambiguous, censored, unordered or identity-inconsistent inputs produce a non-computable result or raise a contract error. No fallback object, hidden selection, semantic label, event identity or episode identity may be generated.

## Supersession and rollback

Class IDs and detector IDs are immutable for this version. Any material change requires a new version and an authorised `SUPERSEDE` record. Rollback disables consumers of this shadow module while preserving records, fixtures, tests, hashes and operator decisions.

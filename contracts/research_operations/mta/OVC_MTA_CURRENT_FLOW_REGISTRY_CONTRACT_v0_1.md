# OVC MTA Current-Flow Registry Contract v0.1

## Purpose

Freeze the object, metric, computability, reason-code and marker-function vocabulary used by the Market Translation and Option-Flow Audit before any population or readiness result is calculated.

## Authority

This contract authorises deterministic audit classification only. It does not create C2E, C2.5, C3, selector, threshold, release, Validation, probability, risk, exposure or execution authority.

## Registry families

1. `FLOW_OBJECT` — lawful object namespaces and grains from OPT-A through MTA and separately referenced RO4.
2. `METRIC` — denominator-explicit audit measurements.
3. `COMPUTABILITY_STATUS` — exhaustive evaluation states.
4. `REASON_CODE` — exact reasons for non-evaluation, exclusion, staleness, conflict or quarantine.
5. `MARKER_FUNCTION` — functional classification of current research markers without semantic promotion.

## Closed computability vocabulary

Every rule attempt must resolve to exactly one of:

- `EVALUATED_FIRED`
- `EVALUATED_NOT_FIRED`
- `NOT_EVALUATED_OUT_OF_SCOPE`
- `NOT_EVALUABLE_SOURCE_MISSING`
- `NOT_EVALUABLE_PARENT_MISSING`
- `NOT_EVALUABLE_AXIS_MISSING`
- `NOT_EVALUABLE_HISTORY_INSUFFICIENT`
- `NOT_EVALUABLE_GAP_OR_RESET`
- `CONFLICT`
- `CENSORED`
- `QUARANTINED`

No missing or ambiguous result may be converted to `NOT_FIRED`.

## Marker boundary

The current marker rules are research diagnostics. Their registry entries must state:

- exact rule ID and evaluator source;
- functional class;
- required axes/history/parent inputs;
- permitted statuses and reasons;
- `c2_5_authority: DENIED`.

A marker may be described as state-change, level-interaction, persistence, sequence-instability, cross-scale context, computability or research-selection-only. This classification is an audit routing label, not a semantic event promotion.

## Metric discipline

Every metric defines numerator, denominator, unit, zero-denominator behaviour, eligible status set and output precision. Rates without an exact denominator are invalid.

## Immutable amendments

A registry version is immutable after gate completion. Corrections require:

1. a new registry version;
2. a `REGISTRY_AMENDMENT` record with prior/new IDs, exact delta, rationale, evidence and affected packets;
3. a supersession map;
4. deterministic rerun of every affected output;
5. operator acknowledgement when the amendment is material.

Historical outputs remain bound to the registry version that produced them.

## Dependency rule

`OPT-A -> C1 -> C2 -> MTA audit objects`.

MTA may evaluate but may not rewrite upstream records. RO4 objects remain separate references and cannot be converted into MTA occurrences or clusters.

## Acceptance

MTA-G1 passes only when all registry entries have stable IDs, owners, grains, source lineage and authority states; all current marker rules are classified; every non-evaluable path maps to a closed reason code; invalid, duplicate, reverse-authority and silent-neutralisation fixtures are rejected; and the result is deterministically reproducible.

## Rollback

Supersede this registry set through a new version and amendment record. Never edit or delete a completed registry version or outputs produced from it.

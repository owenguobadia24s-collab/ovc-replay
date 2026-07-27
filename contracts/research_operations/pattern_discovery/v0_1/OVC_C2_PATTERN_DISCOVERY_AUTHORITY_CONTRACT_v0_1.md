# OVC C2 Pattern Discovery Authority Contract v0.1

## Authority

Namespace: `RO.C2.PATTERN_DISCOVERY`

Authority state before PD-G0: `NONE_DESIGN_CANDIDATE`

Authority after a future PD-G0 PASS: `APPROVED_FOR_BOUNDED_IMPLEMENTATION`; no runtime activation.

## Allowed reads

- active OPT-B.C2 Discovery state, level, container, relation, transition and quality records;
- exact C1 and OPT-A parent lineage exposed by those records;
- approved Research Operations typed read models and QA assertions;
- approved parameter, trigger, fingerprint and distance registries.

## Allowed derived outputs after later packet gates

- transition indexes;
- trigger events;
- deterministic candidate windows;
- trigger and completed fingerprints;
- novelty assessments;
- provisional cluster versions;
- review-queue projections;
- non-evidentiary replay comparisons.

## Prohibited reads and outputs

The layer must not read future bars at trigger time, OPT-C/OPT-D outcomes, return labels, MFE/MAE, trade results, historical 202-story or 58-candidate seed sets, B-STATE, C2E, C2.5 or C3 authority.

It must not mutate C2, activate a selector, publish a release, name an authoritative archetype, create an episode, assign semantic meaning, change thresholds, increment prospective-evidence counts automatically, or create probability, exposure, trading or execution objects.

## Object doctrine

- A TriggerEvent is a reason to observe; it is not an episode.
- A CandidateWindow is derived research triage; it is not evidence.
- A PatternFingerprint is a versioned representation; it is not market truth.
- A ClusterVersion is provisional; it is not an archetype or C3 meaning.
- Human review through the accepted append-only evidence service is required before a candidate becomes a C2 evidence record.

## Chronology

Every trigger freezes `trigger_first_valid_at` and a trigger snapshot containing only records admissible at that time. A completed fingerprint may use records through a deterministic closure time but must never be presented as trigger-time knowledge.

## Operation modes

- `LIVE_PROSPECTIVE`: permitted only after a separate operation gate and only against records first-valid after the bound operation start.
- `TIME_GATED_REPLAY`: non-prospective research and QA.
- `NON_EVIDENTIARY_REPLAY`: version comparison only; never counts as prospective evidence.

Pending change note: PR #88 revises the active prospective-evidence record contract. The evidence bridge remains design-only until that contract is merged or otherwise resolved by an operator decision.

## Retained authority

Validation remains `LOCKED_UNCONSUMED`. Direct Git/R2 writes, active selector mutation, release mutation, C2E, C3, probability, exposure, trading, execution and agent write authority remain denied.
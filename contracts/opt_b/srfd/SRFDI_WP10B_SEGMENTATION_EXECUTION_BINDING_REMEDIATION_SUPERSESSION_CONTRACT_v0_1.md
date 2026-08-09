# SRFDI-WP10B Segmentation Execution-Binding Remediation Supersession Contract v0.1

**Programme:** `OVC-SRFD-BENCHMARK-v0.1`  
**Plan:** `OVC-SRFD-IMPLEMENTATION-PLAN-0.1`  
**Preparation packet:** `SRFDI-WP10B-PREPARATION`  
**Operator gate:** `SRFDI-G10B`  
**Status:** PREPARATION ONLY — OPERATOR REQUIRED — NO AUTHORITY EFFECT

## Purpose

Prepare one bounded execution-route supersession after the consumed WP10 v0.7 run failed closed at
`segmentation/RUN_CHANGE_SEGMENTATION` because the production runner asserted empirical output counts
`264 streams / 7,609 segments / 7,345 boundaries`, while the exact authorised source and frozen algorithm
produced `232 / 7,013 / 6,781`.

This preparation does **not** authorise code changes, a resumed run, a fresh run or any scientific disposition.

## Court-record classification

The frozen v0.3 segmentation registry defines the scientific execution semantics:

- partition by `source_release_id`, `instrument_id`, `side`, `scope_id`, `clock_id`;
- order by `first_valid_time`, then `record_id`;
- split a stream when `reset_reason` starts a new source-contiguous run;
- compute `state_key` from the exact native C2 five-axis payload plus evaluation scope;
- RUN_CHANGE emits a boundary only when `state_key` changes within one uninterrupted stream;
- NULL emits one censored control segment per uninterrupted stream and zero structural boundaries.

The v0.3/v0.4 preregistration binds that registry and does not freeze real-data stream/segment/boundary result
counts. The values `264 / 7,609 / 7,345` are present in the WP10 v0.7 runner execution contract and are therefore
classified as a candidate **execution assertion defect**, not a scientific-rule change.

**Post-hoc rebinding guard:** the observed June values `232 / 7,013 / 6,781` are outputs/evidence only. WP10B
MUST NOT hard-code them as replacement acceptance targets.

## Proposed supersession scope if SRFDI-G10B = SUPERSEDE

Supersede only the WP10 v0.7 data-specific segmentation output-count assertion route. Preserve every frozen
scientific/source/population identity.

A bounded `SRFDI-WP10B` may then:

1. remove data-specific empirical output-count assertions not present in the frozen registry/preregistration;
2. validate the exact registry/source/population identities before segmentation;
3. implement an independent reference uninterrupted-stream and segmentation path for fixtures/adversarial cases;
4. prove reference/production equality for partitions, records, boundaries, segments, ordering and logical hashes;
5. enforce structural invariants rather than post-hoc sample totals:
   - RUN_CHANGE: `segment_count = stream_count + boundary_count` for nonempty uninterrupted streams;
   - NULL: `segment_count = stream_count`, `boundary_count = 0`;
6. prove worker/order/checkpoint/restart equivalence and fail closed on any binding drift;
7. bind a new implementation identity and stop at `SRFDI-G10B-FREEZE`.

## Frozen surfaces

- eligible population: **8,598**
- comparability domains: **36**
- pair opportunities: **35,380,668**
- family configuration identities: **1,944**
- v0.4 preregistration logical SHA-256: `f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3`
- v0.3 segmentation registry logical SHA-256: `6c2451fb5b766d2ae25a13a311ba17c8dede342757d607219e62881be4ac31c0`
- source binding SHA-256: `4d13c3ee8ae2ad25e30088f4f2de48f8320e3633c2e4ea6a5c2c9a7fdc2a62b7`
- representation registry logical SHA-256: `7d93994836bfcff6c5a0b39db33692f70b1a25782bee43c7b6329d17568561c0`
- stability registry logical SHA-256: `371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b`

Mutation of those surfaces is forbidden in WP10B.

## Authority firewalls

- consumed v0.8 token: immutable and non-reusable;
- blocked run: no changed-runner resume;
- fresh June scientific run: DENIED until a separately issued exact `SRFDI-G-JUNE-AUTH`;
- provider fetch: DENIED;
- 2025 Validation: LOCKED_UNCONSUMED;
- selector/family/semantic/publication/scientific promotion: NONE;
- probability/risk/exposure/trading/execution: NONE.

## Required stop

If `SRFDI-G10B` is approved, implement and assure only the bounded remediation above, materialise
`SRFDI-G10B-FREEZE`, and stop. The freeze does not itself authorise another June run.

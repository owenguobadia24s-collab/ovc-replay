# OVC Multiclock Coordinate, Alignment and Correspondence Design Specification v0.1

Programme identity: `OVC-MCAC-v0.1`  
Capability identity: `OVC.MCAC.INACTIVE.DESCRIPTIVE.UTILITY.v0.1`  
Status at freeze: `REVIEW_CANDIDATE`  
Baseline main: `a24c11255cbaeeabc8fe12b99d4d975ef0a5922e`  
Authority effect: `DESIGN_CANON_ONLY`; no activation or source admission

## 1. Purpose and constitutional posture

MCAC is a small repository-native Research Operations utility for comparing owner-authoritative records indexed by different clocks. It provides explicit clock coordinates, causal interval relations, temporal containment, typed evidence-bearing correspondence, deterministic replay identities, and negative-doctrine enforcement. It does not recreate the historical multiclock programmes and it does not own market truth.

The capability is inactive. A representable clock is not an executable clock. Source population admission, clock authority, consumer admission, scientific execution and activation remain with exact current owner authorities. Validation is `LOCKED_UNCONSUMED`.

## 2. Governing inheritance

The governing accession basis is `LSIAC_R2_REPOSITORY_GAP_AND_ACCESSION_MATRIX_v0_1.json`, row `LSIAC-R2-GAP-06`, after repository-effective completion of RRSCG-CORE. The source lineage is indexed by passports `B0354..B0412` and `D001-01..D003-01`.

Historical records establish scoped inheritance only:

- clock is an observer coordinate;
- clock covariance can describe related laws under different coordinates without a shared label lattice;
- temporal containment is not composition;
- morphology resemblance is correspondence evidence, not identity;
- the failed categorical chain remains negative evidence;
- the common-geometry negative is limited to the tested carrier and estimator;
- `TV120_NATIVE` is distinct from owner clock `2H_A_L`;
- implementation cannot grant clock authority.

Historical consumed evidence may prove only that repository mechanics reproduce a frozen relationship. It cannot be reported as fresh scientific confirmation.

## 3. Non-goals and denied effects

MCAC does not create a clock, instrument, provider, side, market, market-state ontology, phase ontology, shared phase hierarchy, selector, predictive model, family discovery, C2/C2E reconstruction, semantic naming, SFF forecast, probability, risk, exposure, trading or execution behaviour. It does not activate Discovery, Development or Validation. It creates no runner, scheduler, cache, evidence store or authority service.

## 4. Core types

### 4.1 `ClockIdentity`

A clock identity is a content-addressed typed coordinate, not a duration. Required fields are:

- `clock_id`: owner-defined exact identity;
- `clock_family`: coordinate family, not an equivalence class;
- `nominal_duration_seconds`: positive integer or explicit null when not duration-based;
- `producer_owner`: owner of the coordinate contract;
- `generation_id`: exact owner generation;
- `source_authority_ref`: authority locator, never inferred from registry presence;
- `chronology_basis`: typed effective/evaluation chronology rule;
- `first_valid_time_semantics`: rule defining when records become lawful inputs;
- `timezone`, `session_basis`, `calendar_basis`: owner-defined values or explicit `NOT_APPLICABLE`/`OWNER_UNSPECIFIED`;
- `provenance_refs`: non-empty ordered-unique source references;
- `comparability_status`: `COMPARABLE_WHEN_RULE_BOUND`, `NOT_COMPARABLE`, or `UNASSESSED`;
- `execution_authority`: `NOT_GRANTED_BY_MCAC` in v0.1.

Identity is the canonical hash of all semantic fields. Equal nominal durations do not imply equal clock identities. No alias or duration canonicaliser exists. A registry must reject duplicate semantic identities, duplicate `clock_id` with differing content, and any declared alias between `TV120_NATIVE` and `2H_A_L`.

### 4.2 `ClockIndexedOccurrenceRef`

An occurrence is a read-only reference to an owner-authoritative record. Required fields are:

- `occurrence_ref_id` and `owner_record_id`;
- exact `clock_identity_id`, `owner_generation_id`, `source_authority_ref` and `source_binding_id`;
- `representation_id` and `representation_generation_id`;
- `interval_start`, `interval_end`, `effective_time`, `first_valid_time`, and `evaluation_cutoff` in UTC;
- `continuity_segment_id` or explicit missingness;
- `source_gap_state`, `censoring_state`, `missingness_state`;
- opaque `owner_payload_ref` and its content hash;
- authority envelope proving read-only use and `LOCKED_UNCONSUMED` Validation.

The ref cannot contain reconstructed private owner fields, copy owner semantics, or define a state/phase label. It is valid only when start is not after end, effective time is not after FVT, and FVT is not after evaluation cutoff.

### 4.3 `ComparabilityContext`

Every comparison binds:

- the ordered pair of exact clock identities;
- both owner/source generations and source bindings;
- lawful overlap interval;
- evaluation cutoff and FVT policy;
- representation pair and correspondence rule identity;
- continuity/gap policy;
- explicit missingness and censoring policy;
- evaluation state: `EVALUABLE`, `NOT_EVALUABLE`, or `NOT_COMPARABLE`.

The context rejects generation stitching, gap bridging, unknown source bindings, representation omission, or a cutoff earlier than either consumed occurrence FVT.

## 5. Alignment

Alignment is a chronology-only relation between two closed intervals whose endpoints and FVT were already available by the comparison cutoff. MCAC uses the following exact interval vocabulary:

- `BEFORE`: left end is strictly before right start;
- `MEETS`: left end equals right start;
- `OVERLAPS`: left starts before right and ends strictly inside right;
- `CONTAINS`: left starts before right (or equal) and ends after right (or equal), excluding equality;
- `DURING`: inverse of `CONTAINS`;
- `STARTS`: starts equal and left ends earlier;
- `FINISHES`: ends equal and left starts later;
- `EQUAL_INTERVAL`: both endpoints equal;
- inverse-direction `AFTER`, `MET_BY`, `OVERLAPPED_BY`, `STARTED_BY`, and `FINISHED_BY` are retained so the relation is total for ordered pairs.

The endpoint convention is explicit: occurrences carry closed descriptive intervals, while `MEETS` is preserved as a boundary relation rather than counted as positive-duration overlap. A relation record includes overlap duration, boundary-touch state, truncation/censoring, and exact input hashes. No interval relation creates market semantics.

Alignment returns typed `NOT_EVALUABLE` or `NOT_COMPARABLE` rather than bridging gaps, stitching generations or substituting missing endpoints. Hindsight is rejected whenever an input FVT exceeds the comparison cutoff.

## 6. Nesting

Three notions are permanently separate:

- `TEMPORAL_CONTAINMENT`: earned only by `CONTAINS` or `EQUAL_INTERVAL` chronology;
- `STRUCTURAL_CORRESPONDENCE`: a separate rule-bound evidence claim over explicit representations;
- `COMPOSITIONAL_HIERARCHY`: unsupported in MCAC v0.1.

A temporal nesting edge can reference occurrences and alignment evidence only. It has `composition_effect: NONE` and `identity_effect: NONE`. No API returns children as the definition of a parent, or a slow-clock state as a deterministic function of fast-clock states.

## 7. Correspondence

Correspondence is typed evidence and never identity. A `CorrespondenceRule` declares its representation inputs, version, deterministic matcher, thresholds/tolerances where applicable, missingness handling, and evidence requirements. Results are:

- `ONE_TO_ONE`, `ONE_TO_MANY`, `MANY_TO_ONE`, `MANY_TO_MANY`;
- `NO_MATCH`, `AMBIGUOUS`, `NOT_COMPARABLE`, `NOT_EVALUABLE`.

Each `CorrespondenceRecord` contains the compared occurrence IDs, clock identities, representation IDs, rule ID/hash, supporting alignment IDs, evidence refs, source/generation bindings, missingness/censoring, candidate cardinalities, evaluation cutoff, doctrine assertions and content hash. Non-empty groups are sorted canonically. An occurrence identity can never be replaced by a correspondence identity.

`AMBIGUOUS` is required when the rule yields multiple incompatible equally admissible assignments. `NOT_COMPARABLE` is required for authority, generation, representation or continuity incompatibility. `NOT_EVALUABLE` is required for missing evidence or FVT unavailability. `NO_MATCH` is an evaluated negative result, not missingness.

## 8. Clock covariance

`ClockCovarianceEvidence` may state `SAME_LAW_DIFFERENT_COORDINATE_MANIFESTATION` only when it binds an exact method, representation pair, source set, comparison population and result artifact. It always carries `shared_categorical_label_effect: NONE`, `identity_effect: NONE`, and `clock_equivalence_effect: NONE`. It cannot manufacture a common categorical state or phase class.

## 9. Negative-knowledge doctrine

The following assertion IDs are machine-readable, mandatory on every MCAC output, and enforced by QA:

- `NO_SHARED_CATEGORICAL_PHASE_LATTICE`;
- `NO_IMPLICIT_TV120_NATIVE_TO_2H_A_L_EQUIVALENCE`;
- `NESTING_NOT_COMPOSITION`;
- `MORPHOLOGY_NOT_IDENTITY`;
- `COMMON_GEOMETRY_NEGATIVE_IS_CARRIER_SCOPED`;
- `FAILED_CORRESPONDENCE_CHAIN_PRESERVED`;
- `NO_CLOCK_AUTHORITY_FROM_IMPLEMENTATION`;
- `HISTORICAL_PARITY_NOT_FRESH_SCIENCE`.

Outputs missing the full active doctrine set fail validation. A downstream adapter cannot weaken an assertion, translate it into a positive ontology claim, or omit the doctrine hash.

## 10. RRSCG and other consumers

The RRSCG adapter accepts only owner-bound RRSCG records that already exist lawfully. It exposes alignment, temporal nesting, correspondence, morphology correspondence, mismatch, ambiguity, not-comparable and missingness. It cannot infer shared RRSCG state identity, shared phase, hierarchical phase composition, cross-clock causal dominance or probability. RRSCG remains inactive.

SPTO and future Research Operations consumers use the same typed interfaces. Interface availability does not admit a consumer source or population. Consumer owners must bind their own authority and source generations.

## 11. IROF transport

MCAC contributes one deterministic `StageSpec` pack and adapter to existing IROF. IROF continues to own PopulationSpec, planning, authority preflight, DAG order, cache, checkpoint/restart, capacity telemetry and receipts. The MCAC stage requires explicit clock identities, a comparison context and owner-bound occurrence refs. Its preflight denies real-source execution in v0.1 and denies Validation.

The transport must preserve semantic hashes across clean replay, chunking, input order and checkpoint/restart. A checkpoint contains only canonical content identities and never grants authority.

## 12. Historical parity and source-unavailable treatment

Exact recovered Pine sources may be retained and byte-hashed as historical implementation lineage. They are not executed as fresh market science. Journal-only closeouts and results are not reconstructed. Where exact result artifacts are unavailable, parity status is `NOT_REPRODUCIBLE_EXACT_ARTIFACT_UNAVAILABLE`; the historical negative doctrine remains preserved through current repository authority, not reverse-engineered from the journal.

## 13. Determinism and failure modes

Canonical JSON uses UTF-8, sorted keys and compact separators. Sets become sorted unique tuples. Inputs are sorted by clock identity, occurrence FVT, owner record ID and occurrence ref ID before evaluation. Duplicate identities, source/generation drift, content tamper, unsupported representations, chronology defects, gaps, censoring and missing owners fail closed into typed results or contract errors as specified.

Reference and optimized paths must be byte-equivalent. The v0.1 implementation may use the reference path as the optimized path until a separately justified optimization exists.

## 14. Acceptance criteria

The design is conformant only if tests cover schema/registry integrity, all interval relations and boundary edges, FVT hindsight rejection, cross-generation rejection, gap/censoring/missingness states, `TV120_NATIVE != 2H_A_L`, nesting not composition, morphology not identity, all correspondence cardinalities/statuses, negative doctrine presence, tamper rejection, RRSCG non-authority, IROF transport, clean/chunked/restarted/order-equivalent replay and bounded large-population capacity.

## 15. Terminal authority

At terminal v0.1 the capability is `INACTIVE`; scientific role is `DESCRIPTIVE_RESEARCH_OPERATIONS_UTILITY`; new clock authority, active Discovery authority and publication are `NONE`; Validation is `LOCKED_UNCONSUMED`; probability/risk/exposure/trading/execution authority is `NONE`.

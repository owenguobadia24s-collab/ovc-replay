# OVC Multiclock Coordinate, Alignment and Correspondence Design Specification v0.1

Programme identity: `OVC-MCAC-v0.1`  
Capability identity: `OVC.MCAC.INACTIVE.DESCRIPTIVE.UTILITY.v0.1`  
Status at freeze: `REVISED_1_REVIEW_CANDIDATE`  
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

### 4.1 `ClockCoordinateIdentity` and `ClockRegistryEntry`

A clock coordinate identity is an immutable semantic coordinate, not a duration and not an authority record. Its content hash covers only:

- `producer_owner`, owner-namespaced `clock_id`, and `generation_id`;
- `clock_family`, which is descriptive and not an equivalence class;
- `nominal_duration_seconds`, a positive integer or explicit null when not duration-based;
- `chronology_basis` and `first_valid_time_semantics`;
- `timezone`, `session_basis`, and `calendar_basis`, each owner-defined or explicitly `NOT_APPLICABLE`/`OWNER_UNSPECIFIED`;
- immutable coordinate-contract provenance references.

The uniqueness key is `(producer_owner, clock_id, generation_id)`. The same textual clock ID can exist in another lawful owner generation only as a different coordinate identity. Equal duration, family or textual suffix never implies equivalence.

Mutable state lives in a separate content-addressed `ClockRegistryEntry` that references the coordinate identity and contains `source_authority_ref`, pairwise comparability state, execution posture, registry revision, effective FVT and evidence provenance. In v0.1 every entry has `execution_authority_effect: NONE_FROM_REGISTRY`; an effective population/consumer authority binding is required separately.

A protected-non-equivalence table is applied to raw names, owner-namespaced names, generations, adapters and canonical forms. Any attempted alias between `TV120_NATIVE` and `2H_A_L` is rejected before registration and again before comparison. No duration-based canonicaliser exists.

### 4.2 `ClockIndexedOccurrenceRef`

An occurrence is a read-only reference to an owner-authoritative record. Required fields are:

- `occurrence_ref_id` and `owner_record_id`;
- exact `clock_coordinate_id`, `clock_registry_entry_id`, `owner_generation_id`, `source_authority_ref` and `source_binding_id`;
- `representation_ref`, a typed, hashed, FVT-bearing reference to an owner-published representation, plus `representation_id`, `representation_generation_id`, `representation_first_valid_time`, and allow-listed `representation_adapter_id`;
- `interval_kind` (`POINT` or `CLOSED_INTERVAL`), `interval_start`, `interval_end`, `effective_time`, `first_valid_time`, and `evaluation_cutoff` in UTC;
- `continuity_segment_id` or explicit missingness plus owner-bound discontinuity spans;
- `source_gap_state`, `censoring_state`, `missingness_state`;
- opaque `owner_payload_ref` and its content hash;
- authority envelope proving read-only use and `LOCKED_UNCONSUMED` Validation.

MCAC core and all MCAC matchers are forbidden to dereference `owner_payload_ref`, inspect a private owner path, or derive a missing representation. Only an allow-listed owner-published representation adapter may resolve `representation_ref`. Unavailable or not-yet-valid representation evidence returns `NOT_EVALUABLE`.

The ref cannot contain reconstructed private owner fields, copy owner semantics, or define a state/phase label. It is valid only when a point has equal endpoints, an interval has start strictly before end, effective time is not after occurrence FVT, every declared dependency FVT is bound, and the occurrence FVT is not after evaluation cutoff.

### 4.3 `ComparabilityContext`

Every comparison binds:

- the ordered pair of exact clock coordinate identities and registry entries;
- both owner/source generations and source bindings;
- lawful overlap interval and owner-bound gap/discontinuity spans for each side;
- evaluation cutoff and FVT policy;
- representation pair, adapter identities and correspondence rule identity;
- continuity/segment compatibility policy;
- explicit missingness and censoring policy;
- doctrine registry identity and effective FVT;
- capacity profile identity;
- evaluation state: `EVALUABLE`, `RETROSPECTIVE_ONLY`, `NOT_EVALUABLE`, or `NOT_COMPARABLE`.

The ordered source-generation pair may differ across clocks, but all records on either side must have exactly that side's generation and one compatible segment; no side may stitch records across generations or segments.

The derived comparison FVT is the maximum of every occurrence FVT, representation FVT, rule FVT, registry revision FVT, source-binding FVT, authority/evidence FVT, doctrine FVT and derivation-confirmation FVT. The cutoff must be at or after that derived FVT. Evidence first available after the declared as-of time produces `RETROSPECTIVE_ONLY`, which is barred from causal stores and causal consumers. Missing dependency chronology is `NOT_EVALUABLE`; incompatible authority, generation, representation or continuity is `NOT_COMPARABLE`.

## 5. Alignment

Alignment is chronology-only and produces exactly one primary relation for an ordered pair. Operands are either `POINT` (start equals end) or `CLOSED_INTERVAL` (start strictly before end). The mutually exclusive decision table is evaluated in this order:

1. both points: `EQUAL_POINT` when timestamps equal, otherwise `BEFORE` or `AFTER`;
2. left point/right interval: `POINT_AT_START`, `POINT_INSIDE`, `POINT_AT_END`, `BEFORE`, or `AFTER`;
3. left interval/right point: inverse `STARTED_BY_POINT`, `CONTAINS_POINT`, `FINISHED_BY_POINT`, `BEFORE`, or `AFTER`;
4. two intervals: `EQUAL_INTERVAL`; `BEFORE`/`AFTER`; `MEETS`/`MET_BY`; `STARTS`/`STARTED_BY`; `FINISHES`/`FINISHED_BY`; `DURING`/`CONTAINS`; or `OVERLAPS`/`OVERLAPPED_BY`, using strict inequalities after the equality cases have been removed.

Every primary relation has a declared inverse and applying inverse twice returns the original relation. `MEETS` has zero positive-duration overlap. The relation record includes operand kinds, overlap duration, boundary-touch state, truncation/censoring, derived comparison FVT and exact input hashes. No interval relation creates market semantics.

Alignment is evaluated only after the ComparabilityContext outcome precedence in section 5.1. Hindsight, gaps, stitching and missing endpoints never receive an interval relation.

### 5.1 Fail-closed outcome precedence

Exactly one top-level outcome is chosen before relation evaluation:

1. invalid/tampered contract raises a typed contract error and emits no scientific record;
2. denied/missing effective population or consumer authority, protected alias, representation incompatibility, per-side generation mismatch, segment mismatch, or a gap/discontinuity crossing produces `NOT_COMPARABLE`;
3. missing owner, endpoint, required representation/evidence or dependency FVT produces `NOT_EVALUABLE`;
4. any dependency FVT after cutoff produces `NOT_EVALUABLE_FUTURE_DEPENDENCY`;
5. evidence valid only after the declared as-of time produces `RETROSPECTIVE_ONLY`;
6. censoring is carried explicitly; if it removes a required endpoint/evidence item it is `NOT_EVALUABLE`, otherwise evaluation proceeds with `censoring_state: PRESENT_BOUNDED`;
7. only then is the single primary relation computed.

Owner-bound gap spans are closed records with their own generation, segment, start/end and FVT. A candidate group intersecting a gap or reset on either side is never bridged.

## 6. Nesting

Three notions are permanently separate:

- `TEMPORAL_CONTAINMENT`: earned only by `CONTAINS` or `EQUAL_INTERVAL` chronology;
- `STRUCTURAL_CORRESPONDENCE`: a separate rule-bound evidence claim over explicit representations;
- `COMPOSITIONAL_HIERARCHY`: unsupported in MCAC v0.1.

Temporal containment is true for interval pairs whose primary relation is `CONTAINS`, `STARTED_BY`, `FINISHED_BY`, or `EQUAL_INTERVAL`, and for the point-containing inverses `STARTED_BY_POINT`, `CONTAINS_POINT`, or `FINISHED_BY_POINT`. Boundary-touch-only `MEETS` is not containment. A temporal nesting edge can reference occurrences and alignment evidence only. It has `composition_effect: NONE` and `identity_effect: NONE`. No API returns children as the definition of a parent, or a slow-clock state as a deterministic function of fast-clock states.

## 7. Correspondence

Correspondence is typed evidence and never identity. Cardinality is always relative to the ordered pair: the first count is occurrences on the left clock and the second is occurrences on the right clock. Results are `ONE_TO_ONE`, `ONE_TO_MANY`, `MANY_TO_ONE`, `MANY_TO_MANY`, `NO_MATCH`, `AMBIGUOUS`, `NOT_COMPARABLE`, `NOT_EVALUABLE`, or `RETROSPECTIVE_ONLY`.

A `CorrespondenceRule` freezes: left/right representation schemas and allow-listed adapters; candidate windows; chronology/containment predicates; similarity or exact-match function; threshold/tolerance; evidence requirements; missingness/censoring handling; assignment objective; tie rule; rule FVT; and merge strategy. Candidate sets are built globally within one ComparabilityContext after fail-closed filtering. Candidate edges are canonically sorted by left occurrence ID, right occurrence ID and evidence hash.

No greedy or encounter-order tie breaking is allowed. If multiple incompatible assignments share the optimum objective/tolerance, the affected component is `AMBIGUOUS`. Overlapping correspondence groups remain distinct evidence components and cannot replace occurrence IDs. `NO_MATCH` means an evaluated empty assignment; it is not missingness.

Finalization is global after all chunks, or uses a versioned associative/commutative merge state proven byte-equivalent to global finalization. Checkpoints contain the canonical candidate-edge multiset, dependency/doctrine identities and unfinished connected components so groups crossing any shard boundary finalize identically.

Each record carries occurrence IDs, coordinate and registry IDs, ordered generation pair, representation and adapter IDs, rule ID/hash/FVT, alignment IDs, evidence refs/FVTs, gap/censoring/missingness state, candidate cardinalities, cutoff, derived FVT, evidence role, doctrine registry identity/hash and content hash. Identity effects are always `NONE`.

## 8. Clock covariance

`ClockCovarianceEvidence` may carry the historical phrase `SAME_LAW_DIFFERENT_COORDINATE_MANIFESTATION` only with `evidence_role: HISTORICAL_CONSUMED_REFERENCE` or `OWNER_PUBLISHED_REFERENCE`, exact scope, method, representation pair, source set, population and artifact identity. MCAC v0.1 cannot generate a fresh covariance or common-geometry scientific claim. Fresh claim generation requires separate authority outside this programme. Every record has `shared_categorical_label_effect: NONE`, `identity_effect: NONE`, and `clock_equivalence_effect: NONE`.

## 9. Negative-knowledge doctrine

The versioned enforcement object is `OVC.MCAC.NEGATIVE_DOCTRINE.v0.1`. Its canonical registry hash is bound after repository materialisation. The following assertion IDs are immutable members:

- `NO_SHARED_CATEGORICAL_PHASE_LATTICE`;
- `NO_IMPLICIT_TV120_NATIVE_TO_2H_A_L_EQUIVALENCE`;
- `NESTING_NOT_COMPOSITION`;
- `MORPHOLOGY_NOT_IDENTITY`;
- `COMMON_GEOMETRY_NEGATIVE_IS_CARRIER_SCOPED`;
- `FAILED_CORRESPONDENCE_CHAIN_PRESERVED`;
- `NO_CLOCK_AUTHORITY_FROM_IMPLEMENTATION`;
- `HISTORICAL_PARITY_NOT_FRESH_SCIENCE`.

Every output, cache key, checkpoint and consumer envelope carries doctrine ID, version, canonical hash, effective FVT, `evidence_role`, source scope and carrier/method scope where relevant. Outputs missing or weakening the exact doctrine set fail contract validation. Historical negative evidence is not generalized beyond its bound carrier, estimator, population and representation. A downstream adapter cannot translate correspondence into ontology or omit doctrine provenance.

## 10. RRSCG and other consumers

The RRSCG adapter accepts only owner-bound RRSCG records that already exist lawfully. It exposes alignment, temporal nesting, correspondence, morphology correspondence, mismatch, ambiguity, not-comparable and missingness. It cannot infer shared RRSCG state identity, shared phase, hierarchical phase composition, cross-clock causal dominance or probability. RRSCG remains inactive.

SPTO and future Research Operations consumers use the same typed interfaces. Interface availability does not admit a consumer source or population. Consumer owners must bind their own authority and source generations.

## 11. IROF transport and source-use crosswalk

MCAC contributes one deterministic `StageSpec` pack and adapter to existing IROF. IROF continues to own PopulationSpec, planning, authority preflight, DAG order, cache, checkpoint/restart, capacity telemetry and receipts. A string `clock_lattice` is descriptive routing only; every invocation and output must additionally bind both full MCAC coordinate identities and registry entries.

Allowed source-use classes are:

- `SYNTHETIC_CONFORMANCE`: permitted by this programme's inactive construction authority;
- `SEALED_CONSUMED_REFERENCE`: permitted only when exact artifact identity and a separately effective historical/reference authority binding are verified; output role is parity/reference only;
- `OWNER_PUBLISHED_DERIVED_RECORDS`: permitted only under separately effective population and consumer authority and still not fresh multiclock science.

`RAW_PROTECTED_SOURCE`, `FRESH_REAL_SOURCE_MULTICLOCK_SCIENCE`, unknown clocks/providers/instruments/sides, and Validation are denied. A source-authority string or registry presence is never sufficient; IROF preflight verifies the separately effective binding, scope and generation without consuming Validation.

The StageSpec binds doctrine ID/hash/FVT, capacity profile, rule and representation registry identities. Checkpoints contain content identities only and never grant authority.

## 12. Historical parity and source-unavailable treatment

Exact recovered Pine sources are retained and byte-hashed as historical implementation lineage. They are not executed as fresh market science. Journal-only closeouts and results are not reconstructed. Where exact result artifacts are unavailable, parity status is `NOT_REPRODUCIBLE_EXACT_ARTIFACT_UNAVAILABLE`; this is not a programme blocker because those artifacts do not define MCAC v0.1 implementation semantics. The historical doctrine is preserved through current repository authority.

Any reproducible parity record must bind `evidence_role: HISTORICAL_CONSUMED_REFERENCE`, exact artifact hash, source scope, representation, method, carrier and FVT. It states only that repository mechanics reproduce a frozen artifact relationship.

## 13. Determinism, capacity and failure modes

Canonical JSON uses UTF-8, sorted keys and compact separators. Sets become sorted unique tuples. Inputs are sorted by coordinate identity, occurrence FVT, owner record ID and occurrence ref ID before evaluation. Duplicate identities, source/generation drift, content tamper, unsupported representations, chronology defects, gaps, censoring and missing owners follow the exact precedence in section 5.1.

Reference and optimized paths must be byte-equivalent. The v0.1 optimized path is the reference algorithm unless a separately qualified optimization exists.

The bound capacity profile is `OVC.MCAC.CAPACITY.SYNTHETIC.v0.1`: maximum 20,000 occurrences per side, 40,000 total occurrences, 2,000,000 candidate pairs, 512 MiB resident-memory growth, 60 seconds for the canonical 20,000-pair synthetic qualification on the repository test runner, and checkpoints at no more than 512 input occurrences per chunk. Exceeding any bound yields `CAPACITY_EXCEEDED`, preserves operational telemetry and checkpoint evidence, marks the result incomplete, and emits no complete/promotable scientific correspondence record.

Assurance includes connected correspondence components crossing every tested shard boundary and proves global/full, chunked, restarted and reversed-input byte identity.

## 14. Acceptance criteria

The design is conformant only if tests cover schema/registry integrity, exhaustive mutually exclusive point/interval relations and inverse involution, full-dependency FVT hindsight rejection, cross-generation rejection, gap/censoring/missingness states, `TV120_NATIVE != 2H_A_L`, nesting not composition, morphology not identity, all correspondence cardinalities/statuses, negative doctrine presence, tamper rejection, RRSCG non-authority, IROF transport, clean/chunked/restarted/order-equivalent global correspondence finalization, shard-crossing groups, bounded large-population capacity, and CAPACITY_EXCEEDED non-result behavior.

## 15. Terminal authority

At terminal v0.1 the capability is `INACTIVE`; scientific role is `DESCRIPTIVE_RESEARCH_OPERATIONS_UTILITY`; new clock authority, active Discovery authority and publication are `NONE`; Validation is `LOCKED_UNCONSUMED`; probability/risk/exposure/trading/execution authority is `NONE`.


## 16. Revised 1 amendment closure map

Revised 1 incorporates design-review findings DR-01 through DR-09: exclusive point/interval algebra; all-dependency FVT; immutable coordinate versus mutable registry; executable gap/censoring/generation precedence; deterministic global correspondence; owner-published representation firewall; versioned doctrine/evidence roles; source-use/IROF authority crosswalk; and exact capacity failure law. The frozen original remains preserved and is not ratified.

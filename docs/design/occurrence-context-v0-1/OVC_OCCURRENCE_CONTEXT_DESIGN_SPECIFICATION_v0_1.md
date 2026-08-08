# OVC OccurrenceContext Design Specification v0.1

**Document ID:** `OVC-OCCURRENCE-CONTEXT-DESIGN-SPEC-0.1`  
**Design namespace:** `OC`  
**Repository:** `owenguobadia24s-collab/ovc-replay`  
**Design baseline:** `main@549b09e6a6e98366db12a07e57bb2d0991c3b6f6`  
**Prepared:** 8 August 2026  
**Status:** `DESIGN COMPLETE / READY FOR OPERATOR REVIEW`  
**Authority effect:** `NONE`  
**Proposed design gate:** `OC-D0` — `OPERATOR_REQUIRED`

## Authority notice

This document freezes a proposed standalone OccurrenceContext design only. It does **not** implement code, create or activate a context selector, change C2/C2E/SRI/FDI/MCARB/C2P semantics, admit a new instrument or clock, consume Validation, promote an MCARB result, make a context field a structural representation input, publish a canonical release, or create family, semantic, probability, risk, exposure, trading or execution authority.

The governing principle is:

> **OccurrenceContext can describe the circumstances of a structural occurrence, but it cannot change what that structural occurrence historically was.**

---

## 0. Executive design decision and court-record reconciliation

### 0.1 Decision

Create **OccurrenceContext** as a standalone, append-only, method-neutral metadata envelope located between immutable upstream occurrence evidence and optional downstream consumers. It binds time, instrument, side, source lineage, clock/scale/lattice, calendar/session, comparison-era, parent-context and separately qualified auxiliary references to an occurrence without inserting those values into C2/C2E structural identity.

OccurrenceContext is not another structural layer. It is a governed contextualization layer. Structural facts remain owned by their source objects; context records only reference them.

### 0.2 Court-record state at design start

| Surface | Court-record state at `main@549b09e...` | Consequence for this design |
|---|---|---|
| End-to-end architecture v0.2 REVISED | Operator-ratified in `06e657d54afa21670576b181be3f938f2ea01c89` | Standalone OccurrenceContext and structural/context separation are governing forward design. |
| MCARB design | `MCARB-D8 PASS` in `00c100ece613bbc5bb8de0c8f8ca45425e036037` | MCARB may supply context references only under explicit later admission. |
| MCARB implementation | Terminal closeout in `664b7d2de0c8f475936d857bc929ad1b7eb88421` | Completed MCARB evidence does not self-activate into OccurrenceContext. |
| C2E v0.2 implementation | WP0-WP5 merged; `CURRENT_STATE_POINTER` remains `C2E2-G6-RUN-AUTH / GATE_READY`; active C2E and active boundary pack are `NONE` | The standalone design may bind the finalized typed C2E v0.2 object contract, but must not imply real-source activation. |
| SRI/FDI conformance | `SFC-G0 DEFER`; programme state `COMPLETED / DEFERRED`; no SFC implementation authority | OccurrenceContext must remain independently implementable and cannot depend on unfinished SFC conformance. |
| Existing OccurrenceContext implementation | `SRFDOccurrenceContext` exists only as a generic SRFD object-type token/schema allowance | No standalone forward OccurrenceContext contract, builder, store or consumer service exists on main. |
| Open relevant PRs | #446 SRFDI capacity remediation; #444 C2E G6 DEFER proposal; #433 preserved SRFD blocker; #418 synthetic rehearsal | All remain proposal/evidence streams and are not silently incorporated as main authority. |

### 0.3 Governing source doctrine

This design conforms to the accepted market-translation architecture and the earlier design-resolution contract:

- OccurrenceContext records **where and when** an occurrence happened without making chronology or regime a hidden structural feature.
- Date/session/context are metadata and stratifiers by default.
- Any context field used structurally requires a **separately versioned RepresentationPack** that explicitly declares `REPRESENTATION_INPUT` and passes its own benchmark/governance path.
- C2P base identity consumes structural evidence directly; context/family enrichment cannot create or rewrite persistent-object identity.
- C2.5 and C3 consume context only through explicit typed dependency manifests.
- MCARB auxiliary records are referenced, not silently copied into structural identifiers.

---

## 1. Purpose and authority boundary

### 1.1 Why OccurrenceContext exists

OccurrenceContext solves five architectural problems without changing structural semantics:

1. attach immutable temporal/source coordinates to a structural occurrence;
2. support multi-year, session and era stratification without date leakage into family discovery;
3. expose episode-relative context such as elapsed duration without altering C2E identity;
4. provide a safe destination for qualified auxiliary evidence such as MCARB AL/ET/VS references;
5. give future C2P, C2.5, C3 and Research Operations one deterministic context contract rather than ad-hoc duplicated fields.

### 1.2 Owns

OccurrenceContext owns:

- contextual envelope identity and versioning;
- anchor binding and dependency inventory;
- time/session/calendar/era derivation under versioned registries;
- first-valid chronology of context fields;
- context-field role declarations;
- typed parent/higher-scale context references;
- typed optional auxiliary-reference slots;
- context missingness, staleness, conflict and supersession records;
- deterministic canonical serialization and replayability.

### 1.3 Does not own

OccurrenceContext does **not** own:

- C2 measurements, axes, levels, containers, relations or transitions;
- C2E episode genesis, membership, phase, boundary or lineage semantics;
- SRI representation semantics, normalization or distance inputs;
- FDI/C2G family identity or assignment;
- MCARB scientific qualification or source semantics;
- C2P base-object identity or lifecycle;
- C2.5 event semantics;
- C3 semantic grammar;
- outcomes, prediction, probability, risk, exposure or execution.

### 1.4 Non-mutation rule

No OccurrenceContext creation, enrichment, supersession, replay or consumer action may write to, rehash, repair, reclassify, relabel or replace an upstream C2/C2E record. A later context record may reference an earlier structural record; it can never revise what that structural record historically was.

---

## 2. Occurrence anchor model

### 2.1 Anchor classes

`OccurrenceAnchorRef` is a typed immutable reference. The initial lawful anchor kinds are:

| `anchor_kind` | Primary key | Required upstream proof | Use |
|---|---|---|---|
| `C2_OBSERVATION` | `c2_record_id == observation_id` | source release, contract/schema, first-valid time, logical/content hash | Per-observation context. |
| `C2E_EPISODE_GENESIS` | `episode_id` | genesis record + boundary-pack/source identity | Whole-episode stable occurrence key. |
| `C2E_EPISODE_SNAPSHOT` | `snapshot_id` + `episode_id` | snapshot record + genesis ref | As-of episode context and elapsed-duration state. |
| `C2E_PHASE_SEGMENT` | `phase_segment_id` + `episode_id` | lawful first-valid phase record | Phase-relative context when a consumer explicitly needs it. |
| `SRI_OCCURRENCE_REPRESENTATION` | `representation_record_id` | exact representation record + underlying structural anchor ref | Alias anchor only; must resolve to a structural anchor. |
| `FDI_OCCURRENCE_ASSIGNMENT` | `assignment_record_id` | exact assignment + underlying representation + structural anchor ref | Evidence/stratification alias only; family/catalog may never become the structural anchor. |

A family ID, prototype, medoid, semantic label, outcome or cohort is never a lawful primary occurrence anchor.

### 2.2 Immutable anchor binding

Every `OccurrenceAnchorRef` contains:

- `anchor_kind`;
- `anchor_id`;
- `anchor_schema_id`;
- `anchor_logical_hash` or immutable content hash;
- `anchor_first_valid_time`;
- `source_release_id` where applicable;
- `structural_anchor_ref` when the immediate anchor is SRI/FDI-derived.

An anchor reference cannot be replaced in-place. If a different upstream occurrence must be referenced, that is a new occurrence/context lineage, not an update.

### 2.3 Multiple context envelopes per occurrence

Yes. One structural occurrence may lawfully have multiple immutable OccurrenceContext records because:

- a later dependency may become first-valid;
- a registry may be superseded;
- a new optional MCARB reference pack may be admitted;
- a consumer may require a different context pack;
- a prior envelope may be stale, partial or quarantined.

The stable `occurrence_key` identifies the underlying occurrence anchor. Each immutable `occurrence_context_id` identifies one exact contextualization of that occurrence.

---

## 3. Deterministic identity and canonical serialization

### 3.1 Two-level identity

**Occurrence key**

`occurrence_key = SHA256("OVC.OCCURRENCE" || canonical(anchor_kind, anchor_id, anchor_schema_id, anchor_logical_hash))`

This key is stable across context versions and contains no session, era, market-condition, MCARB, family or semantic value.

**OccurrenceContext record identity**

`occurrence_context_id = SHA256("OVC.OCCURRENCE_CONTEXT" || canonical(identity_payload))`

`identity_payload` contains only:

- `schema_version`;
- `context_pack_id` and `context_pack_version`;
- `occurrence_key`;
- exact immutable `anchor_ref`;
- `context_role_map_id`;
- `dependency_set_hash`;
- `registry_binding_hash`;
- `first_valid_time`.

### 3.2 Deliberately excluded from structural identity

The following are **never** part of C2/C2E structural identity and are never part of `occurrence_key`:

- calendar year/month/quarter;
- session labels or A-L block;
- canonical clock-position labels;
- market-condition classifications;
- calendar quality labels;
- parent-context interpretation links;
- elapsed episode duration/count;
- current phase label/reference;
- MCARB AL/ET/VS/provider-context references;
- SRI/FDI family or assignment evidence;
- human notes, UI labels and derived display strings.

These values are covered by the record `logical_hash`, so their historical content is tamper-evident, but they cannot mutate the identity of the structural anchor.

### 3.3 Dependency and registry hashes

`dependency_set_hash` is the SHA-256 of sorted typed dependency references including exact IDs, hashes and first-valid times. `registry_binding_hash` is the SHA-256 of the exact calendar/session, market-condition and auxiliary-reference registry identities used.

A changed dependency or registry therefore creates a new context ID even when the occurrence anchor is unchanged.

### 3.4 Canonical serialization

Initial canonical rules:

- UTF-8 JSON canonical form;
- lexicographically sorted object keys;
- no insignificant whitespace;
- UTC timestamps normalized as RFC3339 `YYYY-MM-DDTHH:MM:SS[.fraction]Z`;
- decimals serialized as canonical decimal strings, never binary float artifacts;
- sets encoded as deduplicated lexicographically sorted arrays;
- `null` preserved where the schema explicitly permits it;
- absent and null are distinct;
- local path, hostname, worker, PID, wall-clock runtime and presentation ordering are excluded from logical identity.

`logical_hash` covers the entire immutable semantic record excluding the `logical_hash` field itself.

### 3.5 Forward-only supersession

A new context record never overwrites an earlier one. `OccurrenceContextSupersessionRecord` links old to new with a typed reason and first-valid time. Historical consumers can always resolve the exact context version that was available at their admissible cutoff.

---

## 4. Core context envelope

### 4.1 Required top-level fields

```text
OccurrenceContext {
  schema,
  schema_version,
  occurrence_context_id,
  occurrence_key,
  context_pack_id,
  context_pack_version,
  anchor_ref,
  source_context,
  research_role,
  occurrence_interval,
  calendar_context,
  session_context,
  clock_scale_context,
  parent_context_refs,
  market_condition_context?,
  episode_relative_context?,
  auxiliary_refs,
  context_role_map_id,
  dependency_refs,
  first_valid_time,
  availability,
  reason_codes,
  authority_state,
  lineage,
  logical_hash
}
```

### 4.2 Exact typed field catalogue

| Field | Type | Rule |
|---|---|---|
| `schema` | string | Fixed schema identity, initially `occurrence_context/v0_1`. |
| `schema_version` | string | Schema compatibility version. |
| `occurrence_context_id` | string | Deterministic ID from section 3. |
| `occurrence_key` | string | Stable anchor-derived occurrence key. |
| `context_pack_id` | string | Exact context derivation/field pack. |
| `context_pack_version` | string | Pack version. |
| `anchor_ref` | `OccurrenceAnchorRef` | Immutable typed parent binding. |
| `source_context.instrument_id` | string | Exact governed instrument. Initial implementation may admit only instruments already authorized by its plan. |
| `source_context.price_side` | enum | `BID`, `ASK`, or another separately approved side. No implicit MID synthesis. |
| `source_context.source_release_id` | string | Immutable source release identity. |
| `source_context.manifest_id` | string | Exact source/stream manifest identity. |
| `source_context.source_manifest_hash` | string | Immutable manifest/content digest where available. |
| `research_role` | enum | `DISCOVERY`, `DEVELOPMENT`, `VALIDATION_METADATA_ONLY`, or later governed role. |
| `occurrence_interval.start` | timestamp | Structural occurrence start/effective coordinate; does not imply context was valid then. |
| `occurrence_interval.end` | timestamp/null | Current/terminal occurrence interval end if lawfully known. |
| `calendar_context.calendar_year` | int | Comparison stratum only. |
| `calendar_context.calendar_month` | int | 1-12; comparison stratum only. |
| `calendar_context.calendar_quarter` | int | 1-4; deterministic from registry/calendar contract. |
| `calendar_context.era_partition_ids` | string[] | Optional predeclared period/era strata; never outcome-selected. |
| `session_context.session_membership_ids` | string[] | Memberships from exact frozen session registry. |
| `session_context.a_l_block_id` | string/null | Registry-issued A-L block identity; no ad-hoc time arithmetic. |
| `session_context.registry_id` | string | Exact calendar/session registry identity. |
| `clock_scale_context.clock_id` | string | Existing governed clock identity. |
| `clock_scale_context.scale_id` | string | Existing structural scale. |
| `clock_scale_context.lattice_id` | string | Exact lattice identity. |
| `clock_scale_context.canonical_clock_position` | object/null | Registry-issued coordinate `{position_id, slot_ordinal?, cycle_anchor?, registry_id}`; definition remains registry-owned. |
| `calendar_context.calendar_quality_context` | object | Explicit closures, gaps, special-day states and availability; never silently repaired. |
| `parent_context_refs` | `ContextDependencyRef[]` | Exact first-valid higher-scale/fixed-parent context links. |
| `market_condition_context` | object/null | Optional predeclared classification ref, vocabulary/version/status/FVT; no outcome-derived class. |
| `episode_relative_context` | object/null | Allowed only for lawful C2E anchors; see section 5. |
| `auxiliary_refs` | `MCARBContextRef[]` | Optional typed qualified auxiliary refs; see section 6. |
| `context_role_map_id` | string | Exact field-role declaration. |
| `dependency_refs` | `ContextDependencyRef[]` | Complete input inventory used to derive this envelope. |
| `first_valid_time` | timestamp | Max dependency/anchor/confirmation rule in section 8. |
| `availability.status` | enum | Explicit context availability state. |
| `reason_codes` | string[] | Sorted typed reason codes. |
| `authority_state` | enum | Initial design allows only non-activating states; implementation plan freezes exact enum. |
| `lineage` | object | builder version/commit, registry hashes, supersession refs, replay manifest refs. |
| `logical_hash` | string | Full immutable semantic-record hash. |

### 4.3 Validation role firewall

`VALIDATION_METADATA_ONLY` exists in the schema to preserve forward compatibility with the architecture, but current Validation remains locked/unconsumed. Under the base OccurrenceContext implementation:

- no Validation occurrence anchor may be resolved;
- no Validation row/path/timestamp/object may be read to populate an envelope;
- attempts to do so return `OC_VALIDATION_ACCESS_DENIED`;
- only policy/role metadata may be represented in fixtures or governance records.

A future Validation-access decision is operator-reserved and must create a new authority record; this design grants none.

---

## 5. Episode-relative context

`episode_relative_context` is nullable and may be populated only when the anchor resolves to a lawful C2E v0.2 episode object.

| Field | Type | Rule |
|---|---|---|
| `episode_id` | string | Exact immutable C2E genesis identity. |
| `episode_genesis_ref` | typed ref | Genesis ID/hash/FVT/boundary-pack/source binding. |
| `snapshot_ref` | typed ref/null | Exact snapshot used for as-of context. |
| `elapsed_duration` | duration/null | Deterministic `as_of_time - birth_effective_time` only when both are lawfully first-valid. |
| `elapsed_eligible_observation_count` | int/null | Count from exact eligible membership/input ledger; never inferred from wall-clock duration. |
| `current_phase_ref` | typed ref/null | Exact first-valid `PhaseSegment`; no fabricated semantic phase. |
| `lifecycle_status` | enum/null | Copy/reference of lawful C2E snapshot status only. |
| `censoring_context` | object/null | Censor reason, boundary ref and FVT; censoring is not completion. |
| `completion_context` | object/null | Only if the upstream contract separately establishes terminal completion; absent otherwise. |
| `as_of_time` | timestamp | Exact snapshot/evaluation coordinate. |

Episode-relative fields are context metadata. They do not enter episode genesis, membership, boundary or phase identity. A later RepresentationPack may use a declared episode-relative field only through an explicit `REPRESENTATION_INPUT` admission and context-free comparator.

If no lawful C2E object exists, `elapsed_duration`, `elapsed_eligible_observation_count`, `current_phase_ref`, censoring and completion fields must remain unavailable; they cannot be reconstructed from legacy stories or timestamps.

---

## 6. MCARB integration

### 6.1 Principle

OccurrenceContext stores **typed references or tightly bounded lawful descriptors** to qualified auxiliary evidence. It does not copy arbitrary AL/ET/VS feature vectors into context identity or structural objects.

### 6.2 Typed reference classes

Initial `MCARBContextRef.kind` values:

- `ACTIVITY_LIQUIDITY`;
- `INTRINSIC_EVENT_TIME`;
- `VOLATILITY_STATE`;
- `PROVIDER_SOURCE_CHARACTERISTIC`.

### 6.3 Reference fields

`MCARBContextRef` contains:

```text
{
  kind,
  record_id,
  record_schema_id,
  record_logical_hash,
  domain_id,
  candidate_or_pack_id,
  candidate_or_pack_version,
  source_release_id,
  source_record_ids,
  first_valid_time,
  availability_status,
  qualification_record_id,
  qualification_status,
  context_admission_id,
  compact_descriptor?,
  authority_effect: "NONE"
}
```

`compact_descriptor` is optional and may contain only fields explicitly allowed by the context-admission registry. Arbitrary vectors, embeddings, normalized feature maps or mutable payload copies are forbidden.

### 6.4 Admission requirements

An MCARB reference may populate a non-fixture OccurrenceContext only when **all** are true:

1. the source MCARB record exists under a frozen schema/version and exact hash;
2. its source release and first-valid chronology are resolvable;
3. its qualification/evidence disposition permits contextual reference use;
4. an explicit `OccurrenceContextAuxiliaryAdmission` record names the exact domain/record class/version and allowed context role;
5. the reference is first-valid no later than the OccurrenceContext first-valid time being constructed;
6. missingness/quality state is carried rather than repaired;
7. the admission has no structural, family, semantic or exposure authority.

A benchmark PASS, interesting result, completed MCARB programme or attractive visualization is **not** sufficient to populate production/shadow context automatically.

### 6.5 Initial design dispositions

The MCARB design relationship is preserved:

- canonical clock position — structurally separate context, admissible once its registry is explicit;
- session — context with explicit calendar/session registry;
- elapsed episode duration — only with lawful C2E;
- intrinsic-time coordinate — typed MCARB reference only unless separately admitted;
- activity state — typed AEP/MCARB reference only;
- volatility state — typed AEP/MCARB reference only;
- provider/source characteristics — provenance/context only.

---

## 7. Context-role system

### 7.1 Role vocabulary

Every exposed field path has a base role in a versioned `ContextRoleMap`:

- `IDENTITY_BINDING` — required to bind the context record to its lawful anchor/source/pack; never means structural-market identity.
- `STRATIFIER` — may partition/report populations under a preregistered analysis.
- `FILTER` — may constrain an eligible population only when a consumer manifest explicitly declares the filter before inspecting results.
- `DISPLAY_ONLY` — presentation/inspection metadata; never consumed computationally.
- `REPRESENTATION_INPUT` — pack-scoped consumer role; denied by default and unavailable without separate admission.

### 7.2 Base-role rule

The base OccurrenceContext pack may assign only `IDENTITY_BINDING`, `STRATIFIER`, `FILTER` or `DISPLAY_ONLY`. `REPRESENTATION_INPUT` is never a global field property.

A separately versioned `RepresentationContextAdmission` may bind an exact context field path to `REPRESENTATION_INPUT` for one exact RepresentationPack. This creates a new RepresentationPack identity and must be benchmarked against a context-free comparator.

### 7.3 Default roles for v0.1 design

| Field family | Base role |
|---|---|
| anchor/source/pack IDs, first-valid time | `IDENTITY_BINDING` |
| year/month/quarter/era | `STRATIFIER` |
| session/A-L/clock position | `STRATIFIER` |
| calendar quality | `FILTER` + visible missingness; never hidden |
| parent context refs | `DISPLAY_ONLY` by default; consumer may separately declare `FILTER` |
| market-condition classification | `STRATIFIER` only if predeclared |
| episode elapsed duration/count | `STRATIFIER` by default |
| MCARB refs | `DISPLAY_ONLY`/`STRATIFIER` according to admission; never structural by default |
| UI labels/rendered names | `DISPLAY_ONLY` |

---

## 8. Chronology / First-Valid contract

### 8.1 Universal rule

For every OccurrenceContext record:

```text
context_first_valid_time = max(
    anchor_first_valid_time,
    all populated context-dependency first_valid_times,
    all registry-effective/availability times required by the pack,
    own_derivation_confirmation_time
)
```

The occurrence may have begun earlier. The context record receives no authority before all fields actually used were knowable.

### 8.2 Effective time versus first-valid time

`occurrence_interval.start/end`, episode birth time, session interval or candidate onset describe **effective/onset coordinates**. They do not set context authority time. `first_valid_time` is the only admissibility coordinate for causal use.

### 8.3 Registry chronology

A registry revision is usable only after its own governed effective/available time. Historical envelopes retain the registry version they used. Rebuilding a past occurrence under a newer registry creates a new context version and does not rewrite the earlier envelope.

### 8.4 Retrospective context

Retrospective classifications may be stored only when explicitly labelled `RETROSPECTIVE_CONTEXT` and are forbidden from causal RepresentationPacks or event predicates unless a separately governed research pack explicitly studies retrospective-versus-causal differences.

### 8.5 Backdating denial

Any dependency with `first_valid_time > proposed_context_first_valid_time` blocks the record as `OC_TIME_BACKDATE_DENIED`.

---

## 9. Structural-history firewall

The implementation plan must prove these blocking invariants:

1. **C2 hash invariance:** constructing/replaying context changes zero C2 IDs/hashes/bytes.
2. **C2E hash invariance:** constructing/replaying context changes zero C2E Genesis/Snapshot/Phase/Boundary/Lineage/Membership IDs or logical hashes.
3. **Append-only context:** enrichment creates a successor context record; old records remain addressable.
4. **C2P base-identity firewall:** future C2P `object_id` and genesis identity may not include `occurrence_context_id` or mutable context values. Context is annotation/snapshot enrichment only.
5. **SRI firewall:** context is invisible to structural representation compilation unless the exact RepresentationPack declares a field-level context admission.
6. **FDI firewall:** distance/family methods do not read OccurrenceContext directly. They receive only the exact RepresentationRecord produced by the declared pack.
7. **C2.5/C3 manifest firewall:** no wholesale context envelope inheritance. Each event predicate/clause declares exact context field paths as `REQUIRED`, `OPTIONAL` or `FORBIDDEN`.
8. **Outcome firewall:** future outcomes, return labels, MFE/MAE, probability, edge, risk, trade/execution state and Validation evidence are forbidden fields/dependencies.
9. **No repair by context:** missing/stale/conflicting upstream evidence remains missing/stale/conflicting; context never synthesizes a structural substitute.
10. **Cross-run determinism:** same frozen anchor, dependencies, registries, context pack and cutoff produce byte/logically identical context records.

Any violation is `BLOCK`/`QUARANTINE`, never warning-only.

---

## 10. Missingness and failure algebra

### 10.1 Availability states

Initial semantic states:

- `AVAILABLE`;
- `PARTIAL`;
- `NOT_EVALUABLE`;
- `UNAVAILABLE`;
- `STALE`;
- `CONFLICT`;
- `CENSORED`;
- `QUARANTINED`.

`PARTIAL` is lawful only when every missing optional field is named. A required-field failure yields `NOT_EVALUABLE` or stronger.

### 10.2 Reason-code namespaces

| Namespace | Examples | Meaning |
|---|---|---|
| `OC_AVAIL_*` | `OC_AVAIL_ANCHOR_MISSING`, `OC_AVAIL_REQUIRED_DEPENDENCY_MISSING` | Object/dependency availability. |
| `OC_TIME_*` | `OC_TIME_PARENT_NOT_FIRST_VALID`, `OC_TIME_BACKDATE_DENIED`, `OC_TIME_REGISTRY_NOT_EFFECTIVE` | Chronology/FVT failure. |
| `OC_REGISTRY_*` | `OC_REGISTRY_SESSION_STALE`, `OC_REGISTRY_MARKET_CONDITION_UNKNOWN` | Registry/version problem. |
| `OC_SESSION_*` | `OC_SESSION_UNRESOLVED`, `OC_SESSION_MULTIPLE_CONFLICT` | Calendar/session resolution. |
| `OC_C2E_*` | `OC_C2E_REQUIRED_FOR_ELAPSED_DURATION`, `OC_C2E_CENSORED`, `OC_C2E_PHASE_UNAVAILABLE` | Episode-relative context. |
| `OC_MCARB_*` | `OC_MCARB_REF_UNAVAILABLE`, `OC_MCARB_NOT_ADMITTED`, `OC_MCARB_REF_STALE` | Auxiliary-reference failure. |
| `OC_ROLE_*` | `OC_ROLE_REPRESENTATION_INPUT_UNAUTHORIZED`, `OC_ROLE_UNDECLARED_FIELD` | Context-role/consumer violation. |
| `OC_DEP_*` | `OC_DEP_FORBIDDEN_FIELD`, `OC_DEP_HASH_MISMATCH` | Dependency contract violation. |
| `OC_ID_*` | `OC_ID_ANCHOR_MUTATION`, `OC_ID_LOGICAL_HASH_MISMATCH` | Identity/integrity failure. |
| `OC_AUTH_*` | `OC_AUTH_VALIDATION_ACCESS_DENIED`, `OC_AUTH_NEW_INSTRUMENT_DENIED`, `OC_AUTH_NEW_CLOCK_DENIED` | Reserved authority violation. |

Reason codes are additive, deterministic and sorted. They never erase source-specific reason codes.

---

## 11. Versioning and registries

### 11.1 Separate identities

OccurrenceContext must not collapse distinct governance concerns into one version number.

| Versioned object | Owns | Requires new version when |
|---|---|---|
| `OccurrenceContextSchema` | JSON/Python shape, types, required/nullability contract | field shape/type/requiredness or same-name semantic interpretation changes. |
| `OccurrenceContextPack` | selected fields, derivation rules, dependency requirements, base roles, canonicalization profile | derivation/field-set/dependency/role/canonical rule changes without needing a schema break. |
| `CalendarSessionRegistry` | sessions, A-L mapping, timezone/calendar/closure semantics | any membership boundary, label meaning, timezone or closure rule changes. |
| `MarketConditionVocabulary` | predeclared context classifications and status meanings | class definition or eligibility rule changes. |
| `OccurrenceContextAuxiliaryAdmissionRegistry` | which MCARB record classes/versions may be referenced and in what role | any domain/class/version/admission condition changes. |
| `ContextRoleMap` | base field roles and consumer-specific admission references | a field role changes or a new representation admission is added. |

### 11.2 Pack versus schema

Examples requiring a **new context pack, same schema**:

- adding calendar quarter derivation from already-supported calendar fields;
- changing which optional parent-context link is populated;
- changing a base field from `DISPLAY_ONLY` to `STRATIFIER`;
- admitting an additional MCARB reference class through a new admission registry;
- changing canonical clock-position derivation while retaining the same field type.

Examples requiring a **new schema**:

- changing `session_membership_ids` from array to scalar;
- changing timestamp semantics/type;
- making a formerly optional top-level object structurally mandatory;
- renaming a field while retaining normative meaning under the same schema family;
- altering the structure of `OccurrenceAnchorRef` incompatibly.

Representation-input admission creates a new **RepresentationPack**, not a silent OccurrenceContext pack mutation.

---

## 12. Comparability and multi-year use

### 12.1 Context is an analysis axis, not family truth

Year, month, quarter, session, A-L block, era and predeclared market-condition fields may be used to:

- stratify family/representation evidence;
- report continuity, fragmentation, emergence/disappearance and residual drift by period;
- construct leave-period-out transport tests;
- match control populations by time-of-day/session;
- inspect source-quality differences by calendar state.

They may **not** define a structural family merely because a family is concentrated in a date/session stratum.

### 12.2 Predeclaration rule

Any filtering on context that changes an eligible scientific population must be declared in the consumer's population/preregistration manifest before outcome/family evidence is inspected. Post-result slicing remains descriptive evidence and must be labelled accordingly.

### 12.3 Multi-instrument rule

The schema is instrument-generic, but the implementation may only operate on instruments admitted by its authority envelope. Adding a new instrument, side, market, calendar or clock is operator-reserved. Cross-instrument claims require an explicit comparability domain; context equality never implies structural-family identity across instruments.

---

## 13. Consumer interfaces

### 13.1 Common consumer contract

Every consumer uses a `ContextConsumptionManifest` containing:

- `consumer_kind` and exact consumer pack/version;
- accepted context schema/pack versions;
- exact field paths consumed;
- per-field dependency role `REQUIRED | OPTIONAL | FORBIDDEN`;
- intended context role (`STRATIFIER`, `FILTER`, `DISPLAY_ONLY`, or separately admitted `REPRESENTATION_INPUT`);
- admissible cutoff/FVT rule;
- missingness behavior;
- authority effect;
- manifest hash.

No consumer may deserialize the whole envelope and opportunistically use undeclared fields.

### 13.2 SRI

- May reference `occurrence_context_id` for provenance and stratification.
- Context-enriched SRI (`R7`) requires an exact separately versioned RepresentationPack and field-level `RepresentationContextAdmission`.
- Without that admission, context fields are not representation dimensions.

### 13.3 FDI / C2G

- May use OccurrenceContext for preregistered population stratification, chronological stability and descriptive reporting.
- May not read context directly inside distance/family algorithms.
- A family catalog remains scoped to representation/method/population/config identities, not context labels.

### 13.4 Future C2P

- C2P base identity consumes C2/C2E structural evidence only.
- `occurrence_context_id` may appear in C2P annotation/snapshot enrichment.
- No mutable context field, family assignment, session or MCARB record may create/rewrite `object_id`.
- C2P implementation must include an explicit negative test proving this firewall before any persistent-object activation.

### 13.5 Revised C2.5

- Every event type declares exact OccurrenceContext fields as `REQUIRED/OPTIONAL/FORBIDDEN`.
- Default is no context dependency.
- Making a new context dependency part of an event predicate is a separately governed event/semantic change and cannot be activated by OccurrenceContext implementation.

### 13.6 Future C3

- C3 AST clauses may reference context only through typed clause dependencies.
- Context is not a semantic label source by default.
- Family/context clauses remain optional unless a separately governed grammar version requires them.

### 13.7 Research Operations

- May read/display/compare/stratify OccurrenceContext under the selected research role and admissible cutoff.
- May expose exact lineage, missingness and reason codes.
- May append research annotations linked to immutable context IDs.
- May not mutate source structural records or silently promote context into model semantics.

---

## 14. Proposed schemas and Python object catalogues

### 14.1 `OccurrenceContext`

Proposed JSON schema path:

`schemas/context/occurrence_context/occurrence_context_v0_1.schema.json`

Proposed Python object:

```text
@dataclass(frozen=True)
class OccurrenceContext:
    schema: str
    schema_version: str
    occurrence_context_id: str
    occurrence_key: str
    context_pack_id: str
    context_pack_version: str
    anchor_ref: OccurrenceAnchorRef
    source_context: SourceContext
    research_role: str
    occurrence_interval: OccurrenceInterval
    calendar_context: CalendarContext
    session_context: SessionContext
    clock_scale_context: ClockScaleContext
    parent_context_refs: tuple[ContextDependencyRef, ...]
    market_condition_context: MarketConditionContext | None
    episode_relative_context: EpisodeRelativeContext | None
    auxiliary_refs: tuple[MCARBContextRef, ...]
    context_role_map_id: str
    dependency_refs: tuple[ContextDependencyRef, ...]
    first_valid_time: str
    availability: ContextAvailability
    reason_codes: tuple[str, ...]
    authority_state: str
    lineage: ContextLineage
    logical_hash: str
```

### 14.2 `ContextDependencyRef`

```text
ContextDependencyRef {
  dependency_kind,
  record_id,
  schema_id,
  logical_hash,
  first_valid_time,
  dependency_role,
  source_release_id?,
  required: bool
}
```

### 14.3 `ContextRoleMap`

```text
ContextRoleMap {
  context_role_map_id,
  version,
  schema_compatibility,
  field_roles: { field_path -> IDENTITY_BINDING|STRATIFIER|FILTER|DISPLAY_ONLY },
  representation_admissions: [RepresentationContextAdmissionRef],
  canonical_hash
}
```

`REPRESENTATION_INPUT` is represented only inside a pack-scoped `RepresentationContextAdmission`, never as an unqualified global role.

### 14.4 `OccurrenceContextSupersessionRecord`

```text
OccurrenceContextSupersessionRecord {
  supersession_id,
  occurrence_key,
  prior_occurrence_context_id,
  successor_occurrence_context_id,
  reason_code,
  changed_dependency_ids,
  changed_registry_ids,
  first_valid_time,
  authority_effect: "NONE",
  logical_hash
}
```

### 14.5 `MCARBContextRef`

Defined in section 6.3. Proposed schema path:

`schemas/context/occurrence_context/mcarb_context_ref_v0_1.schema.json`

### 14.6 `OccurrenceContextPackRegistry`

```text
OccurrenceContextPackRegistryEntry {
  context_pack_id,
  version,
  accepted_anchor_kinds,
  required_fields,
  optional_fields,
  dependency_rules,
  calendar_session_registry_id,
  market_condition_vocabulary_id?,
  auxiliary_admission_registry_id?,
  context_role_map_id,
  chronology_rule_id,
  canonical_serialization_id,
  allowed_research_roles,
  prohibited_fields,
  authority_state,
  canonical_hash
}
```

---

## 15. Adversarial design fixtures

The implementation plan must materialize at least these fixtures:

| ID | Fixture | Required result |
|---|---|---|
| `OC-F01` | Byte-identical structural episode instantiated in two different sessions | Same structural anchor/episode ID; distinct context records; no structural hash change. |
| `OC-F02` | Later session/registry evidence becomes first-valid | New successor context; prior context unchanged. |
| `OC-F03` | Attempt to add outcome/future-return/MFE/MAE field | Hard `BLOCK` with forbidden-field reason. |
| `OC-F04` | MCARB feature vector embedded directly in context payload | Hard `BLOCK`; typed reference required. |
| `OC-F05` | Elapsed episode duration requested for C2-only anchor | `NOT_EVALUABLE / OC_C2E_REQUIRED_FOR_ELAPSED_DURATION`. |
| `OC-F06` | SRI pack tries to read session as a feature without context admission | Hard `BLOCK / OC_ROLE_REPRESENTATION_INPUT_UNAUTHORIZED`. |
| `OC-F07` | Calendar/session registry version changes | New context ID/supersession; historical interpretation preserved. |
| `OC-F08` | Validation occurrence anchor requested under current authority | Hard `BLOCK / OC_AUTH_VALIDATION_ACCESS_DENIED`; no object/timestamp resolution. |
| `OC-F09` | Parent context first-valid after child proposed FVT | Hard chronology block; no backdating. |
| `OC-F10` | C2E episode is gap-censored | `CENSORED`; never silently marked complete. |
| `OC-F11` | SRI/FDI alias anchor resolves to different structural anchor than declared | Hard anchor-lineage block. |
| `OC-F12` | Same frozen inputs rebuilt under different file path/worker order | Identical context ID/logical hash. |
| `OC-F13` | Missing optional MCARB reference | Context remains `PARTIAL` only when pack permits; exact reason retained. |
| `OC-F14` | Missing required session registry | `NOT_EVALUABLE`; no guessed session/A-L block. |
| `OC-F15` | Consumer loads undeclared context field | Hard dependency-role block. |
| `OC-F16` | Future C2P identity builder is given two different context envelopes for same structural object | Same C2P base-identity candidate or explicit implementation failure; context cannot change object identity. |

---

## 16. QA and acceptance criteria

### 16.1 Required QA families

| Check ID | Assertion | Blocking |
|---|---|---|
| `OC-QA-01` | Same frozen inputs rebuild byte/logically identically. | YES |
| `OC-QA-02` | Context FVT equals/maximizes all required dependency FVTs and own confirmation time. | YES |
| `OC-QA-03` | Every dependency resolves by exact ID/schema/hash. | YES |
| `OC-QA-04` | C2/C2E upstream IDs/hashes unchanged before/after context construction. | YES |
| `OC-QA-05` | Every exposed field path exists in exact role map. | YES |
| `OC-QA-06` | `REPRESENTATION_INPUT` impossible without exact RepresentationPack admission. | YES |
| `OC-QA-07` | MCARB refs resolve by exact qualified ID/hash/version/admission. | YES |
| `OC-QA-08` | No arbitrary MCARB vector copy or forbidden outcome/authority field. | YES |
| `OC-QA-09` | Registry changes create successor records, not historical mutation. | YES |
| `OC-QA-10` | Session/A-L/clock position never guessed when registry unavailable. | YES |
| `OC-QA-11` | C2E censoring/completion semantics preserved exactly. | YES |
| `OC-QA-12` | Validation access denied under current authority. | YES |
| `OC-QA-13` | New instrument/side/clock/lattice outside plan envelope denied. | YES |
| `OC-QA-14` | Consumer manifests reject undeclared fields and whole-envelope leakage. | YES |
| `OC-QA-15` | C2P base identity negative fixture proves context-independence before C2P implementation may rely on OC. | YES |
| `OC-QA-16` | Repository artifact boundary excludes raw market streams, large context streams and caches from Git. | YES |

### 16.2 Acceptance criteria

Base OccurrenceContext implementation is conformant only when:

- contract, schemas, registries, fixtures, implementation, tests, QA packet and machine-readable programme state all exist;
- all blocking QA checks pass;
- builder/replay is deterministic;
- upstream C2/C2E no-mutation proof passes;
- current authorised instruments/clocks/sides only are accepted;
- context field roles are complete and no undeclared field is consumable;
- MCARB references remain inert unless explicitly admitted;
- Validation remains denied;
- no selector/family/semantic/publication/exposure authority changes;
- rollback is non-destructive and historical context records remain addressable.

---

## 17. Repository integration proposal

No implementation is performed by this design document. The later implementation plan should use bounded locations such as:

```text
contracts/context/occurrence_context/
  OCCURRENCE_CONTEXT_CONTRACT_v0_1.md
  OCCURRENCE_CONTEXT_CONSUMER_CONTRACT_v0_1.md
  OCCURRENCE_CONTEXT_STRUCTURAL_FIREWALL_v0_1.md

schemas/context/occurrence_context/
  occurrence_context_v0_1.schema.json
  occurrence_anchor_ref_v0_1.schema.json
  context_dependency_ref_v0_1.schema.json
  context_role_map_v0_1.schema.json
  occurrence_context_supersession_v0_1.schema.json
  mcarb_context_ref_v0_1.schema.json
  occurrence_context_pack_v0_1.schema.json

registries/context/occurrence_context/
  OCCURRENCE_CONTEXT_PACK_REGISTRY_v0_1.json
  CONTEXT_ROLE_MAP_v0_1.json
  CALENDAR_SESSION_BINDINGS_v0_1.json
  MARKET_CONDITION_VOCABULARY_BINDINGS_v0_1.json
  AUXILIARY_ADMISSION_REGISTRY_v0_1.json
  REASON_CODE_REGISTRY_v0_1.json

fixtures/context/occurrence_context/v0_1/
  golden/
  adversarial/

src/ovc/context/occurrence_context/
  models.py
  serialization.py
  anchors.py
  chronology.py
  builder.py
  calendar_adapter.py
  c2e_adapter.py
  mcarb_refs.py
  consumers.py
  replay.py

 tests/context/occurrence_context/
 docs/releases/occurrence-context-v0-1/
 registries/implementation/occurrence_context/
```

### 17.1 Storage boundary

Git may contain contracts, schemas, registries, compact fixtures, code, tests, QA, compact manifests/hashes and decisions. Full market/context streams, caches and bulky replay artifacts remain outside Git and are referenced by immutable hashes. R2/canonical publication remains separately reserved.

---

## 18. Implementation-plan handoff and gate sequence

### 18.1 Proposed implementation-plan title

**OVC Standalone OccurrenceContext Implementation Plan v0.1**  
Proposed plan ID: `OVC-OCCURRENCE-CONTEXT-IMPLEMENTATION-PLAN-0.1`

### 18.2 Recommended work packets

| Packet | Deliverable | Proposed gate | Classification |
|---|---|---|---|
| `OC-WP0` | Latest-main/source reconciliation; exact C2/C2E/SRI/FDI/MCARB surface census; conflict/open-PR map; current instrument/clock/Validation authority freeze | `OC-G0` | **OPERATOR_REQUIRED** plan ratification. No implementation before PASS. |
| `OC-WP1` | Contracts, schemas, role map, context pack, reason codes, canonical serialization and golden fixtures | `OC-G1` | `AUTO_RATIFIABLE` if no semantic expansion beyond approved design. |
| `OC-WP2` | Deterministic anchor resolver, context builder, append-only supersession and replay/hash engine | `OC-G2` | `AUTO_RATIFIABLE`. Build/test only; no new market authority. |
| `OC-WP3` | C2/C2E/calendar/session/clock adapters and episode-relative context | `OC-G3` | `AUTO_RATIFIABLE` only for already authorised instruments/clocks and read-only inactive/shadow upstream objects. New instrument/clock/side => operator stop. |
| `OC-WP4` | MCARB typed-reference extension and auxiliary admission enforcement | `OC-G4` | `AUTO_RATIFIABLE` only for inert reference plumbing to already-qualified records under an approved admission registry. Any **scientific activation**, new MCARB authority or `REPRESENTATION_INPUT` => **OPERATOR_REQUIRED** separate gate. |
| `OC-WP5` | Adversarial QA, Research Operations read-only projection, consumer-manifest firewall and full-repository assurance | `OC-G5` | `AUTO_RATIFIABLE` if read-only and no reserved delta. |
| `OC-WP6` | Consolidated conformance/rollback packet proving structural-history firewall and C2P-readiness boundary | `OC-G6` | **OPERATOR_REQUIRED** terminal conformance decision before C2P design/implementation may treat OccurrenceContext as an accepted upstream contract. |

### 18.3 Reserved authority interlocks

The base plan must stop for explicit operator approval before any of the following:

- any context field becomes `REPRESENTATION_INPUT`;
- any new instrument, market, price side, clock, lattice or undeclared dependency is admitted;
- Validation data beyond metadata-only policy visibility is accessed;
- an MCARB result is activated as an authoritative context classification/reference class where that activation was not already admitted;
- C2/C2E/SRI/FDI/C2P/C2.5/C3 frozen semantics are changed;
- selector or canonical publication state changes;
- family, semantic, probability, risk, exposure or execution authority is proposed.

### 18.4 C2P boundary

Passing base OccurrenceContext implementation does **not** implement C2P. `OC-G6 PASS` would mean only that C2P design may safely reference the frozen OccurrenceContext contract as non-identity enrichment. C2P remains a separate programme with its own identity/lifecycle design and authority gates.

---

## 19. Final design decision

**Decision: ACCEPT_FOR_OPERATOR_REVIEW.**

The standalone OccurrenceContext architecture is coherent and implementation-ready as a non-structural, append-only metadata envelope. Its central safety property is achieved by separating:

1. stable structural occurrence identity (`occurrence_key` from immutable anchor evidence),
2. versioned contextualization (`occurrence_context_id` from pack/dependency/registry/FVT identity), and
3. downstream consumer authority (field-level manifests and separately governed representation admissions).

This permits the same structural occurrence to be studied across session, era, clock position, elapsed duration and auxiliary conditions without relabelling the occurrence or contaminating its structural history.

### 19.1 Unresolved questions intentionally left to implementation planning or later authority

1. Exact repository-owned calendar/session registry artifact to bind for the first context pack; the design does not invent session/A-L boundaries.
2. Exact initial context `authority_state` enum names; implementation may freeze non-activating states only.
3. Which completed MCARB record classes, if any, receive explicit first auxiliary-admission entries. Completion/benchmark evidence alone is insufficient.
4. Exact compact-descriptor allowlist for provider/source characteristics; arbitrary vectors remain forbidden.
5. Whether SRI/FDI conformance is reopened before or after OccurrenceContext implementation. Base OccurrenceContext does not depend on SFC reopening.
6. C2E real-source activation remains separately governed at `C2E2-G6-RUN-AUTH`; OccurrenceContext design must work against the frozen object contract without presuming activation.
7. Future market-condition vocabularies remain optional and must be predeclared; no regime taxonomy is selected here.

### 19.2 Exact authority state after this design

- OccurrenceContext design: `DESIGN_COMPLETE / READY_FOR_OPERATOR_REVIEW`.
- OccurrenceContext implementation: `NONE`.
- Structural representation input from context: `DENIED_BY_DEFAULT`.
- C2/C2E mutation: `DENIED`.
- New instrument/clock/side: `DENIED`.
- MCARB automatic activation into context: `DENIED`.
- SRI/FDI scientific authority: `UNCHANGED / SFC DEFERRED`.
- C2P implementation: `NOT_STARTED / NOT_AUTHORISED_BY_THIS DESIGN`.
- Validation: `LOCKED_UNCONSUMED`; context access beyond metadata policy is `DENIED`.
- Selector/family/semantic/publication: `NONE`.
- Probability/risk/exposure/trading/execution: `NONE`.

### 19.3 Recommended next OVC command

After operator review of this exact design:

`OVC APPROVE OC-D0 PASS`

A PASS should accept the design only and permit preparation of **OVC Standalone OccurrenceContext Implementation Plan v0.1**. It must not start C2P or grant any reserved authority.

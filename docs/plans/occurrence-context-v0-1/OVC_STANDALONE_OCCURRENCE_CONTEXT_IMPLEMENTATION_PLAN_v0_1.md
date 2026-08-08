# OVC Standalone OccurrenceContext Implementation Plan v0.1

**Plan ID:** `OVC-OCCURRENCE-CONTEXT-IMPLEMENTATION-PLAN-0.1`  
**Programme:** `OVC-OCCURRENCE-CONTEXT`  
**Design authority:** `OVC-OCCURRENCE-CONTEXT-DESIGN-SPEC-0.1`  
**Design decision:** `OC-D0 PASS / OPERATOR`  
**Accepted design merge:** `2b348c92f3c6ac1831002f87f5d192d1046cb91b`  
**Design closeout main:** `dd03abb71361c7111af64f9f71e8ea28a436a8f4`  
**Prepared from main:** `dd03abb71361c7111af64f9f71e8ea28a436a8f4`  
**Plan status:** `GATE_READY / OC-G0 OPERATOR_REQUIRED`  
**Implementation authority before OC-G0:** `NONE`

---

## 0. Purpose

Implement the accepted standalone OccurrenceContext design as a deterministic, append-only, read-only contextualization layer before C2P begins.

The implementation must allow time, session, instrument, source lineage, era, scale, parent context, C2E-relative context and later separately admitted auxiliary references to be attached to immutable occurrence anchors without altering structural identity or historical C2/C2E records.

The governing invariant is unchanged:

> **OccurrenceContext can describe the circumstances of a structural occurrence, but it cannot change what that structural occurrence historically was.**

This plan does not design or implement C2P. It prepares a stable upstream contract that C2P may later reference only after terminal OC conformance.

---

## 1. Authority envelope proposed at OC-G0

### 1.1 Authority that PASS would grant

`OC-G0 PASS` authorizes only the following bounded repository work for `OC-WP0` through `OC-WP5`:

- repository/source reconciliation;
- contracts, JSON schemas, Python frozen objects and deterministic canonical serialization;
- registries and compact fixtures;
- deterministic occurrence-anchor resolution against existing typed contracts and synthetic/fixture evidence;
- append-only context builder, validation and supersession machinery;
- read-only adapters to already-existing C2/C2E contracts and calendar/session/clock registry evidence;
- inactive typed MCARB reference plumbing with **no scientifically activated auxiliary admission**;
- consumer manifests and read-only Research Operations projection;
- adversarial/golden tests, QA packets, deterministic replay and hash/no-mutation proofs;
- eligible automatic squash merges for wholly non-reserved PASS gates.

### 1.2 Authority that PASS does not grant

The following remain denied and require separate operator authority if later proposed:

- C2P design or implementation;
- any change to C2/C2E structural semantics, IDs, hashes, boundary logic or historical records;
- any context field becoming `REPRESENTATION_INPUT`;
- new instrument, market, price side, clock, lattice or undeclared upstream dependency;
- real-source C2E replay or C2E activation;
- Validation occurrence/data access;
- scientific activation of an MCARB result as a context input/classification;
- new market-condition/regime taxonomy with scientific meaning;
- selector activation/replacement;
- family, semantic, theory, candidate or model promotion;
- canonical/R2 publication or new immutable release identity;
- probability, risk, exposure, trading, execution or agent-write authority;
- destructive mutation, deletion, force-push or history rewriting.

### 1.3 Base-plan deferral choices

To keep this implementation inside a non-scientific engineering envelope, v0.1 deliberately chooses:

1. **MCARB admission registry starts empty/inert.** WP4 implements reference validation and admission mechanics, but no real AL/ET/VS record class is activated merely because MCARB completed.
2. **Market-condition vocabulary starts empty/inert.** The schema supports nullable typed classifications, but no regime vocabulary is invented or scientifically activated.
3. **Provider/source compact descriptors default to provenance-only allowlisted fields already bound by source identity.** No auxiliary feature vector is admitted.
4. **C2E episode adapters use typed contract fixtures/inactive records only.** C2E real-source replay remains `DENIED_DEFERRED_AT_C2E2_G6`.
5. **Validation remains hard-denied.** `VALIDATION_METADATA_ONLY` is a policy enum and fixture state, not data access.
6. **SFC remains deferred.** OccurrenceContext implements its own stable contract and only read-only optional interfaces to SRI/FDI; it does not reopen SFC.

These choices mean `OC-G1` through `OC-G5` can remain auto-ratifiable unless an implementation discovery would require a reserved semantic or authority change.

---

## 2. Governing inputs and precedence

Implementation must resolve conflicts in this order:

1. repository court record on latest lawful `main`;
2. exact `OC-D0` operator decision and accepted design specification;
3. ratified End-to-End Market Translation Architecture v0.2 REVISED and design-resolution package;
4. current C2/C2E typed contracts and immutable source-binding semantics;
5. accepted MCARB reference doctrine;
6. current SRI/FDI contracts where they exist, preserving SFC DEFER;
7. this implementation plan after `OC-G0 PASS`;
8. packet-local deterministic implementation details that do not change frozen semantics.

Code and tests prove conformance but do not create authority.

---

## 3. Programme topology and gate model

```text
OC-G0  OPERATOR plan ratification
  |
  v
OC-WP0 repository/source reconciliation
  -> OC-G1 AUTO
OC-WP1 contracts/schema/registry/fixtures
  -> OC-G2 AUTO
OC-WP2 deterministic envelope builder/supersession/replay
  -> OC-G3 AUTO
OC-WP3 C2/C2E/calendar/session/clock adapters
  -> OC-G4 AUTO unless a new instrument/clock/semantic boundary is required
OC-WP4 inert MCARB extension/admission surface
  -> OC-G5 AUTO only while no scientific activation occurs
OC-WP5 adversarial QA + read-only consumer integration
  -> OC-G6 OPERATOR terminal conformance
STOP before C2P
```

Every packet uses a fresh bounded branch from the latest lawful main after all prerequisites merge.

---

## 4. OC-WP0 — Repository and source reconciliation

### 4.1 Purpose

Turn the accepted design into an exact implementation baseline without inventing missing registry semantics.

### 4.2 Required inspections

WP0 must inventory and bind:

- accepted OC design/decision/merge receipt;
- latest main SHA and open/conflicting PRs;
- current C2 observation identity, chronology, source binding and parent-context contracts;
- current C2E v0.2 schemas/models, current terminal G6-DEFER authority and synthetic fixtures;
- current SRI representation occurrence records and FDI assignment occurrence records, explicitly preserving SFC DEFER;
- current calendar/session/time-horizon/clock/lattice registries or contracts;
- any existing A-L block definition actually present on main;
- source-release/manifest identity surfaces;
- MCARB record/qualification/admission-relevant artifacts and their current authority;
- Research Operations read-only adapter conventions;
- existing generic `SRFDOccurrenceContext` references to avoid naming/schema collision.

### 4.3 Mandatory reconciliation outputs

Create compact machine-readable inventories:

- `OC_WP0_SOURCE_SURFACE_CENSUS.json`;
- `OC_WP0_AUTHORITY_FREEZE.json`;
- `OC_WP0_REGISTRY_GAP_LEDGER.json`;
- `OC_WP0_COLLISION_AND_DEPRECATION_LEDGER.json`;
- `OC_WP0_QA_PACKET.json`.

### 4.4 Fail-closed rules

WP0 must not invent session boundaries, A-L definitions, calendar closures, clock identities, SRI/FDI object semantics or MCARB qualification meaning.

If the accepted design requires a calendar/session binding that does not exist in a sufficiently explicit court-record artifact, WP0 records `OC_REGISTRY_SESSION_SOURCE_NOT_MATERIALISED` and blocks the affected later adapter. A new semantic calendar/session definition is operator-required; a schema/registry transcription of already-frozen semantics is auto-executable.

### 4.5 Acceptance

`OC-G1 PASS` requires:

- exact main/design/source identities bound;
- no unresolved collision with an existing forward OccurrenceContext implementation;
- all missing source/registry semantics classified as `MATERIALISE_EXISTING_SEMANTICS`, `OPTIONAL_DEFER`, or `OPERATOR_REQUIRED`;
- no Validation/data access performed;
- QA recommends PASS or PASS_WITH_NONBLOCKING_DEFERRALS;
- complete repository CI and merge-readiness green.

**Gate classification:** `AUTO_RATIFIABLE` if no reserved authority is required.

---

## 5. OC-WP1 — Contracts, schemas, registries and fixtures

### 5.1 Contracts

Materialize:

- `contracts/context/occurrence_context/OCCURRENCE_CONTEXT_CONTRACT_v0_1.md`;
- `OCCURRENCE_CONTEXT_CONSUMER_CONTRACT_v0_1.md`;
- `OCCURRENCE_CONTEXT_STRUCTURAL_FIREWALL_v0_1.md`;
- `OCCURRENCE_CONTEXT_CHRONOLOGY_CONTRACT_v0_1.md`;
- `OCCURRENCE_CONTEXT_MC_ARB_REFERENCE_CONTRACT_v0_1.md`.

Contracts must explicitly deny future/outcome fields and structural mutation.

### 5.2 Schemas

Materialize JSON schemas for:

- `OccurrenceContext`;
- `OccurrenceAnchorRef`;
- `ContextDependencyRef`;
- `ContextRoleMap`;
- `OccurrenceContextSupersessionRecord`;
- `MCARBContextRef`;
- `OccurrenceContextPackRegistryEntry`;
- `ContextConsumptionManifest`;
- optional `MarketConditionContext` with no active vocabulary.

Schemas must use closed-object discipline where practical and fail unknown semantic fields rather than silently pass them through.

### 5.3 Initial registries

Materialize versioned registries:

- `OCCURRENCE_CONTEXT_PACK_REGISTRY_v0_1.json`;
- `CONTEXT_ROLE_MAP_v0_1.json`;
- `CALENDAR_SESSION_BINDINGS_v0_1.json`;
- `MARKET_CONDITION_VOCABULARY_BINDINGS_v0_1.json` with `NO_ACTIVE_VOCABULARY` unless existing semantics are merely transcribed;
- `AUXILIARY_ADMISSION_REGISTRY_v0_1.json` with `NO_SCIENTIFIC_ADMISSIONS`;
- `REASON_CODE_REGISTRY_v0_1.json`;
- `AUTHORITY_STATE_REGISTRY_v0_1.json` containing only non-activating implementation states.

### 5.4 Base context pack

The initial pack must:

- accept only lawful anchor kinds frozen by design;
- use structural/source IDs only as `IDENTITY_BINDING`;
- classify date/session/era/clock-position as `STRATIFIER` by default;
- classify calendar-quality exclusions only as explicit `FILTER` where declared;
- classify parent context and auxiliary refs as `DISPLAY_ONLY` or `STRATIFIER` unless a consumer manifest says otherwise;
- contain no `REPRESENTATION_INPUT` admission;
- bind empty/inert market-condition and MCARB admission registries;
- bind the exact canonical serialization profile.

### 5.5 Golden and adversarial fixtures

Materialize the design fixtures `OC-F01` through `OC-F16`, plus minimal positive examples for every lawful anchor kind that is actually available from current contracts.

Fixture data must be compact synthetic/contract fixtures only. No raw provider data is committed.

### 5.6 Acceptance

`OC-G2 PASS` requires:

- schema validation for every fixture;
- all field paths covered by a role map;
- unknown/forbidden fields fail closed;
- no active MCARB or market-condition admission;
- no `REPRESENTATION_INPUT` path in the base pack;
- canonical fixture serialization byte-identical across repeated runs;
- repository suite green.

**Gate classification:** `AUTO_RATIFIABLE`.

---

## 6. OC-WP2 — Deterministic envelope builder, supersession and replay

### 6.1 Implementation package

Create `src/ovc/context/occurrence_context/` with bounded modules:

- `models.py` — frozen typed objects/validation helpers;
- `serialization.py` — canonical serialization and SHA-256 identities;
- `anchors.py` — immutable typed anchor resolution;
- `dependencies.py` — exact ID/schema/hash/FVT dependency inventory;
- `chronology.py` — first-valid/effective-time algebra;
- `builder.py` — deterministic envelope construction;
- `supersession.py` — append-only successor links;
- `replay.py` — deterministic rebuild/validation;
- `firewall.py` — forbidden fields and authority leakage checks.

### 6.2 Identity algorithm

Implement exactly the accepted two-level design:

- stable `occurrence_key` from immutable anchor kind/ID/schema/hash only;
- `occurrence_context_id` from schema version, context pack, occurrence key, exact anchor ref, role map, dependency-set hash, registry-binding hash and final context FVT;
- `logical_hash` over complete immutable semantic content excluding only the hash field itself.

No context value may enter `occurrence_key`.

### 6.3 Chronology

Builder computes:

```text
context_first_valid_time = max(
  anchor_first_valid_time,
  populated_dependency_first_valid_times,
  required_registry_availability_times,
  own_derivation_confirmation_time
)
```

No API accepts a caller-supplied earlier FVT override.

### 6.4 Supersession

An update request that changes a dependency, registry binding or context value must either:

- deterministically reproduce the existing context record; or
- create a new context record plus `OccurrenceContextSupersessionRecord`.

In-place semantic mutation is prohibited.

### 6.5 Acceptance

`OC-G3 PASS` requires:

- deterministic IDs/hashes across repeated builds;
- F01/F02/F03/F07/F09/F12/F15 passing;
- backdating impossible;
- no upstream write path imported by the package;
- exact negative proof that context construction changes no source fixture bytes/hashes;
- repository suite green.

**Gate classification:** `AUTO_RATIFIABLE`.

---

## 7. OC-WP3 — C2/C2E/calendar/session/clock adapters

### 7.1 C2 adapter

Implement read-only anchor extraction from the current C2 contract:

- observation/C2 record ID;
- instrument, side, source release/manifest;
- clock, scale, lattice;
- source/effective interval;
- first-valid time;
- exact logical/content hash;
- lawful parent-context refs already present in the source contract.

The adapter does not reinterpret structural axes or recompute C2.

### 7.2 C2E adapter

Implement read-only typed adapters for lawful C2E v0.2:

- `EpisodeGenesis`;
- `EpisodeSnapshot`;
- `PhaseSegment` where required by accepted design.

Episode-relative fields derive only from exact typed records and membership/input ledgers. Censoring is preserved as censoring and is not upgraded to completion.

No real-source C2E replay is performed. Fixtures/inactive records only.

### 7.3 Calendar/session/clock adapter

Resolve only exact existing registry semantics bound in WP0/WP1.

Outputs may include:

- year/month/quarter;
- explicit era partition IDs;
- session membership IDs;
- A-L block ID if and only if an exact registry defines it;
- canonical clock position;
- calendar quality, closures and gaps.

Unknown or stale registry evidence produces explicit missingness; the adapter never guesses.

### 7.4 Higher-scale context

Parent/higher-scale links remain typed references. The adapter must enforce parent FVT `<=` child context FVT and preserve the exact referenced parent hash.

### 7.5 Acceptance

`OC-G4 PASS` requires:

- C2/C2E hash-invariance proofs;
- F01/F05/F09/F10/F11/F14 passing;
- no real-source replay token or provider access;
- no new instrument/side/clock/lattice admitted;
- calendar/session semantics exactly traceable to frozen registries or unavailable;
- repository suite green.

**Gate classification:** `AUTO_RATIFIABLE` only if all inputs are existing contract/fixture/read-only surfaces. Any need to define a new clock, A-L/session semantics or structural parent interpretation is `OPERATOR_REQUIRED` and stops the programme.

---

## 8. OC-WP4 — MCARB typed-reference extension surface

### 8.1 Scope

Implement the **mechanism** for MCARB/context references, not scientific activation.

Modules:

- `mcarb_refs.py`;
- auxiliary admission registry loader/validator;
- qualification/ref hash verification;
- compact descriptor allowlist enforcement;
- first-valid/missingness checks.

### 8.2 Base admission state

`AUXILIARY_ADMISSION_REGISTRY_v0_1` remains `NO_SCIENTIFIC_ADMISSIONS`.

The package may validate synthetic examples for:

- `ACTIVITY_LIQUIDITY`;
- `INTRINSIC_EVENT_TIME`;
- `VOLATILITY_STATE`;
- `PROVIDER_SOURCE_CHARACTERISTIC`.

But a non-fixture reference is rejected unless a later explicit admission record exists.

### 8.3 Vector firewall

Reject:

- arbitrary feature maps;
- vectors/embeddings;
- normalized MCARB representation arrays;
- unknown compact-descriptor keys;
- mutable unversioned payload copies.

Only exact typed references and allowlisted provenance descriptors may cross the boundary.

### 8.4 Acceptance

`OC-G5 PASS` requires:

- F04/F13 passing;
- absent admission fails `OC_MCARB_NOT_ADMITTED`;
- exact record hash/version/FVT checks deterministic;
- no production/shadow scientific auxiliary input becomes active;
- no RepresentationPack is changed;
- repository suite green.

**Gate classification:** `AUTO_RATIFIABLE` for inert plumbing only. Any proposed real MCARB scientific admission is a separate `OPERATOR_REQUIRED` gate and is not part of base v0.1 implementation.

---

## 9. OC-WP5 — Adversarial QA and read-only consumer integration

### 9.1 Consumer manifest enforcement

Implement `ContextConsumptionManifest` validation for:

- SRI research/read-only interface;
- FDI/C2G research/read-only interface;
- future C2P interface stub only;
- revised C2.5 interface stub only;
- future C3 interface stub only;
- Research Operations read-only projection.

An interface stub defines allowed dependency shape; it does not implement the downstream layer.

### 9.2 Consumer rules

- SRI: context unavailable to representation compilation unless a separately admitted RepresentationPack says otherwise.
- FDI/C2G: family/distance code cannot import/read OccurrenceContext directly.
- C2P: stub asserts context does not participate in base identity.
- C2.5/C3: undeclared field consumption fails closed.
- Research Operations: read/display/stratify only; no structural mutation or promotion.

### 9.3 Adversarial suite

Run all `OC-F01` through `OC-F16` plus:

- unknown field injection;
- future timestamp dependency;
- stale registry binding;
- conflicting session memberships;
- duplicate/sorted dependency inventory checks;
- path/hostname/worker-order independence;
- attempted Validation anchor resolution;
- attempted new instrument/clock/side;
- attempted whole-envelope consumer deserialization;
- attempted C2P identity contamination;
- upstream-byte mutation sentinel.

### 9.4 Full QA requirements

Generate a consolidated `OC_WP5_QA_PACKET.json` proving:

- deterministic rebuild;
- chronology/FVT;
- dependency integrity;
- logical/context ID integrity;
- C2/C2E no-mutation;
- missingness algebra;
- role-map completeness;
- authority leakage denial;
- no active MCARB/market-condition science;
- Validation denial;
- artifact-boundary compliance;
- complete repository CI;
- rollback.

### 9.5 Acceptance

WP5 is `IMPLEMENTED / QA_REVIEW` only when every blocking design QA check `OC-QA-01` through `OC-QA-16` passes.

After WP5, prepare one consolidated terminal `OC-G6` operator conformance packet and stop.

**Gate classification:** WP5 engineering gate is `AUTO_RATIFIABLE`; terminal `OC-G6` is `OPERATOR_REQUIRED`.

---

## 10. Terminal OC-G6 — OccurrenceContext conformance before C2P

### 10.1 Purpose

OC-G6 does not activate a model or selector. It decides whether the standalone OccurrenceContext implementation is sufficiently conformant to become a frozen upstream dependency for later C2P design.

### 10.2 Required evidence

The consolidated packet must contain:

- plan/version and accepted design identity;
- baseline and final candidate/main commits;
- all packet merge receipts;
- complete changed-file inventory;
- all focused and repository test results;
- F01-F16 results;
- OC-QA-01 through OC-QA-16 results;
- C2/C2E before/after hash inventories;
- chronology/FVT proof;
- context-pack/registry hashes;
- empty/inert MCARB and market-condition admission evidence;
- consumer-manifest coverage;
- Validation/new-instrument/new-clock denial evidence;
- unresolved warnings;
- rollback;
- exact authority delta.

### 10.3 Proposed PASS effect

A future `OC-G6 PASS` would permit only this statement:

`OccurrenceContext v0.1 is an accepted, deterministic, non-structural upstream context contract that later C2P design may reference as non-identity enrichment.`

It would **not** itself start C2P, activate auxiliary scientific fields, publish canonically or grant any exposure authority.

---

## 11. Branch, PR, commit and merge discipline

Each packet uses one bounded branch:

- `build/oc-wp0-reconciliation`
- `build/oc-wp1-contracts-schema-registry`
- `build/oc-wp2-builder`
- `build/oc-wp3-adapters`
- `build/oc-wp4-mcarb-reference-surface`
- `build/oc-wp5-adversarial-integration`
- gate/closeout branches where needed.

For every auto-ratifiable packet:

1. verify latest main and prerequisites;
2. implement bounded changes;
3. run focused tests;
4. run complete repository suite and profile/merge readiness;
5. produce QA and delegated PASS decision;
6. ensure no unresolved review thread;
7. squash-merge with pinned head SHA;
8. record merge receipt and next packet;
9. start next branch from the new main.

No force-push.

---

## 12. Machine-readable programme state

The implementation programme must maintain:

- `registries/implementation/occurrence_context/OVC_OC_IMPLEMENTATION_STATE_v*.json`;
- `registries/implementation/occurrence_context/CURRENT_IMPLEMENTATION_STATE_POINTER.json`.

Every packet entry contains:

`packet_id, plan_id, plan_version, status, prerequisites, authority_required, authority_delta, baseline_commit, branch, candidate_commit, tests, qa_packet, decision_record, merge_commit, blockers, next_packet`.

Allowed states are the global OVC states: `PLANNED, READY, RUNNING, IMPLEMENTED, QA_REVIEW, GATE_READY, APPROVED, BLOCKED, QUARANTINED, SUPERSEDED, COMPLETED`.

---

## 13. Test strategy

### 13.1 Focused tests

Create `tests/context/occurrence_context/` with packet-scoped files for:

- schema and registry validation;
- canonical serialization;
- identity and hash determinism;
- anchor binding;
- chronology/FVT;
- supersession;
- C2/C2E adapters;
- calendar/session missingness;
- MCARB typed refs;
- consumer manifests;
- structural-history firewall;
- authority denial;
- F01-F16.

### 13.2 Repository assurance

Every packet final head must pass:

- complete repository test workflow;
- OVC deterministic profile selection/FINAL_HEAD assurance;
- compatibility context;
- merge readiness.

A failure caused by stale lifecycle assertions may be corrected only if the historical record remains immutable and the assertion is advanced to the lawful current pointer; tests may not be weakened to hide a real defect.

---

## 14. Rollback model

Rollback is always forward and non-destructive:

- code defects: revert by new commit/PR while preserving evidence;
- context record defect: quarantine and create corrected successor; never rewrite old semantic records;
- registry defect: new registry/context-pack version and supersession;
- adapter defect: quarantine affected context output and preserve upstream source objects unchanged;
- authority violation: BLOCK/QUARANTINE immediately and preserve evidence.

Raw market streams, bulky replay outputs, caches and external artifacts remain outside Git.

---

## 15. Operator-required stop conditions during implementation

Even after `OC-G0 PASS`, stop immediately before:

- defining new session/A-L/calendar semantics not already frozen;
- adding a new instrument/market/side/clock/lattice;
- accessing Validation occurrence data;
- enabling real-source C2E replay;
- scientifically activating an MCARB AL/ET/VS/provider characteristic;
- assigning `REPRESENTATION_INPUT` to any context field;
- modifying a frozen C2/C2E/SRI/FDI contract materially;
- starting C2P;
- changing C2.5/C3 semantics;
- selector or canonical publication changes;
- family/semantic/model/theory promotion;
- probability/risk/exposure/execution/agent-write authority;
- destructive or history-rewriting action.

---

## 16. OC-G0 plan-ratification acceptance conditions

`OC-G0 PASS` should be granted only if the operator accepts all of these:

1. the plan implements the already-accepted design without widening it;
2. WP0-WP5 authority is engineering/build/test/read-only/synthetic only;
3. MCARB and market-condition scientific admissions start empty/inert;
4. no real-source C2E replay or activation is authorized;
5. no Validation occurrence data may be read;
6. no new instrument/clock/side may be admitted;
7. context remains non-structural by default and `REPRESENTATION_INPUT` remains separately governed;
8. C2/C2E historical bytes/IDs/hashes are immutable inputs;
9. C2P remains outside the programme and cannot start before terminal OC-G6 plus separate C2P authority;
10. intermediate wholly non-reserved PASS gates may auto-ratify and squash-merge continuously;
11. any unexpected reserved delta forces an operator stop;
12. terminal `OC-G6` is operator-required.

---

## 17. Proposed authority state after OC-G0 PASS

```text
OccurrenceContext design              ACCEPTED_MERGED
OC-WP0..WP5 repository implementation AUTHORIZED_BUILD_TEST_ONLY
Synthetic/adversarial OC computation  AUTHORIZED_INACTIVE_NONCANONICAL
Read-only C2/C2E adapters              AUTHORIZED_CONTRACT_FIXTURE_ONLY
Real-source C2E replay                 DENIED_DEFERRED_AT_C2E2_G6
MCARB scientific context admission     NONE / DENIED
Market-condition scientific vocabulary NONE / DENIED
REPRESENTATION_INPUT from context      DENIED_PENDING_SEPARATE_PACK
New instrument/clock/side              DENIED
Validation occurrence access           DENIED / LOCKED_UNCONSUMED
SFC reopening                          NOT_AUTHORIZED
C2P                                    NOT_STARTED / NOT_AUTHORIZED
C2.5/C3 semantic change                NOT_AUTHORIZED
Selector/publication                   NONE / DENIED
Probability/risk/exposure/execution    NONE
Agent write                            NONE
```

---

## 18. Recommended OC-G0 decision

**Recommended:** `PASS`.

Rationale: the plan converts the accepted OccurrenceContext design into a bounded deterministic implementation route while deliberately deferring all scientific/context activation choices that could contaminate structural identity or cross an operator-reserved authority boundary.

### Exact next command

`OVC APPROVE OC-G0 PASS`

On PASS, execution should begin at `OC-WP0` and continue automatically through eligible non-reserved gates, stopping at the first unexpected reserved boundary or terminal `OC-G6`.

# OVC Integrated Research Orchestration Framework
## Design Specification v0.1

**Programme:** OVC-IROF-v0.1  
**Document ID:** OVC-IROF-DESIGN-SPEC-0.1  
**Repository:** `owenguobadia24s-collab/ovc-replay`  
**Court-record baseline:** `main@ffefd1ee3d7ee664f2a94f74d05993d6e711a149`  
**Baseline tree:** `1176e5a9342561bf3a9e6d1ba21b09615e226108`  
**Prepared:** 2026-08-09  
**Status:** DESIGN COMPLETE / GATE_READY / NOT IMPLEMENTED  
**Authority effect:** NONE until IROF-G0 operator ratification

> **Authority notice.** IROF is cross-cutting research infrastructure. This specification grants no provider intake, real replay, selector, ACTIVE_DISCOVERY/DEVELOPMENT/VALIDATION, representation, normalization, distance, family, C2E, C2P, C2.5, C3, publication, probability, risk, exposure, execution or agent-write authority. The orchestrator may enforce authority already granted by the owning programme; it may never create or combine partial authorities into a new grant.

---

## 0. Executive decision

### 0.1 Decision

Adopt a permanent, typed, DAG-based **OVC Integrated Research Orchestration Framework (IROF)** around the existing OVC scientific and evidence packages. IROF standardises how a governed population is bound, how a lawful pipeline subgraph is planned and executed, how immutable outputs are reused, how checkpoints and capacity failures are handled, and how execution lineage, telemetry, QA and Research Operations evidence are materialised.

The core equation is:

```text
PopulationSpec
  + PipelineProfile
  + versioned stage packs/configuration
  + AuthorityBindings
  = ResearchRunSpec
  -> IntegratedRunManifest
  -> deterministic stage DAG execution
  -> StageExecutionReceipts + artifacts + QA
  -> IntegratedRunReceipt
```

IROF knows **HOW** and **WHETHER** an execution node may run. It does not decide **WHAT** the node's market output means.

### 0.2 Architectural judgement

Repository evidence supports conform-and-generalise rather than a greenfield runner. The repository already contains:

- SRFD fixture orchestration, canonical stage hashing and checkpoints in `src/ovc/opt_b/srfd/orchestration.py`;
- topological capacity planning and no-scope-change failure handling in `src/ovc/opt_b/srfd/scheduler.py`;
- semantic cache keys, corruption quarantine and tile completion ledgers in `src/ovc/opt_b/srfd/semantic_cache.py`;
- capacity/environment/IO profiling in `src/ovc/opt_b/srfd/capacity*.py`, `family_*capacity.py` and related modules;
- SFC replay manifests, checkpoint/restart, capacity guards and June interlock enforcement in `src/ovc/opt_b/sfc/replay.py`;
- C2E v0.2 stream manifests, checkpoint/restart equivalence and synthetic assurance receipts in `src/ovc/opt_b/c2e_v2/`;
- an historical full-stack synthetic rehearsal in draft PR #418 that demonstrated the value of one end-to-end harness but was intentionally noncanonical and omitted later standalone OccurrenceContext;
- Research Operations canonical identity, artifact catalogue, QA runner, storage and deterministic read model under `src/ovc/research_operations/`;
- a completed standalone OccurrenceContext package under `src/ovc/context/occurrence_context/` with explicit consumer-role firewalls.

IROF therefore extracts only generic orchestration concerns. Frozen scientific implementations remain owned by their current packages and are invoked through typed adapters.

### 0.3 Terminal target

`IROF = IMPLEMENTED / INACTIVE_INFRASTRUCTURE_AVAILABLE`

This means one canonical research-run framework exists, but no new scientific or market authority exists merely because it can execute a stage.

---

## 1. Court-record reconciliation

### 1.1 Baseline

| Item | Court-record state at design start |
|---|---|
| main | `ffefd1ee3d7ee664f2a94f74d05993d6e711a149` |
| latest main decision | `SRFDI-G-JUNE-AUTH v0.6: fresh post-SFC delegated authorization` |
| IROF branch before this packet | none found |
| IROF work branch | `design/irof-v0-1-g0`, created from exact baseline |
| SFC | COMPLETED / PRESERVED |
| C2E v0.2 | GATE_READY at C2E-AG0; operator disposition DEFER; real-source replay denied |
| OccurrenceContext | COMPLETED; v0.1 frozen deterministic nonstructural upstream contract |
| C2 Discovery | active v2 Discovery selector; Development reference only; Validation locked/unconsumed |
| SRFD | READY for one exact bounded June SRFD run under a separately issued unconsumed token; no scientific promotion |
| Validation | LOCKED_UNCONSUMED |

### 1.2 Important open lines

The following open PRs are evidence inputs, not IROF dependencies to merge:

- **#479 C2E2-G6 BLOCK June PASS supersession pre-run.** It identifies an exact revised-C2 June source but blocks real C2E replay because no separately governed June-eligible empirical boundary pack is frozen and the exact C2E resource envelope is unspecified. IROF must preserve this denial.
- **#433 SRFDI-WP10 capacity evidence.** It records the large June family-grid capacity problem and is a required capacity-design input; it is not authority to reduce the scientific grid.
- **#418 FSR v0.1 synthetic full-stack rehearsal.** It is a draft historical rehearsal, useful as an integration-fixture source only. IROF must not merge or promote its FSR-specific adapters as canonical current interfaces.
- older June/SRFD/review PRs remain historical evidence unless separately reactivated by their owner programme.

### 1.3 Current implementation classification

**CURRENT COURT-RECORD IMPLEMENTATION**

- active OPT-A/C1/C2 release and authority machinery;
- revised C2 shadow/current implementation assets as recorded by their own programme;
- C2E v0.2 implementation through synthetic/inactive conformance capability;
- SFC/SRI/FDI/FamilyEvidenceStream conformance implementation, completed/preserved;
- standalone OccurrenceContext v0.1, completed;
- SRFD orchestration/capacity/cache/scheduler implementation;
- Research Operations evidence, QA, catalogue, storage and read model.

**ACCEPTED BUT INACTIVE CAPABILITY**

- C2E v0.2 execution machinery beyond current synthetic/nonempirical scope;
- SRI/FDI scientific method surfaces where no canonical method has been promoted;
- SRFD exact bounded June authorization is owned by SRFD only and does not grant an integrated June run;
- historical market-grammar shadow components remain noncanonical.

**PROPOSAL / DESIGN**

- IROF itself before IROF-G0;
- future C2P, revised C2.5 and forward C3 where not yet independently implemented/accepted;
- future OPT-C/OPT-D integration into IROF profiles.

**HISTORICAL / SUPERSEDED**

- old B-STATE/C2 authorities and legacy C2E identities as marked by their owning registries;
- FSR-specific draft orchestration in PR #418;
- earlier SRFD June/preflight tokens and consumed/deferred attempts.

**FUTURE TARGET**

- one standard orchestration interface spanning synthetic and separately authorised real populations;
- C2P/C2.5/C3/OPT-C/OPT-D/MCARB registration through StageSpec without scheduler redesign.

### 1.4 Governing conflict assessment

No design-level conflict prevents IROF-G0. A material **authority asymmetry** must be preserved: SRFD currently has one exact bounded June token while C2E real-source replay remains denied. Therefore IROF cannot lawfully assemble those partial permissions into `FULL_DESCRIPTIVE` June authority. The framework must model authority per node and fail closed at C2E while preserving reusable authorised ancestors.

---

## 2. Purpose and non-goals

IROF provides:

1. one typed PopulationSpec model for synthetic and real/replay populations;
2. one canonical stage registry and DAG planner;
3. versioned PipelineProfiles as subgraphs;
4. exact authority preflight before protected inputs are resolved;
5. deterministic semantic run identity separated from attempt identity and physical location;
6. immutable artifact reuse by complete semantic dependency identity;
7. run/stage/substage checkpoint and restart coordination;
8. capacity-aware scheduling without scientific scope mutation;
9. per-stage and whole-run computational telemetry;
10. Research Operations/QA/artifact-catalogue integration;
11. deterministic synthetic end-to-end assurance;
12. dry-run/preflight for separately governed real populations;
13. extension by StageSpec + adapter rather than core scheduler modification.

IROF is not a market Option, classifier, representation, family method, selector, semantic layer, scientific promotion mechanism, outcome engine or exposure mechanism.

---

## 3. Architectural position

IROF is a cross-cutting execution plane analogous to Research Operations/QA, not another market layer.

```text
                         IROF EXECUTION PLANE
         +--------------------------------------------------+
Population -> Authority -> DAG -> Scheduler -> Artifacts    |
         |       |        |        |          |             |
         |       +------ receipts / hashes / telemetry -----+
         +--------------------> Research Operations / QA

Scientific/data DAG (profile dependent):
OPT-A/source -> C1 -> revised C2 -> C2E -> SRI -> comparisons -> FDI/C2G
                          |          |                         |
                          +-> OccurrenceContext branch         +-> FamilyEvidenceStream
                          +-> MCARB branch (separately governed)
Future: C2P / C2.5 / C3 / OPT-C / OPT-D
```

OccurrenceContext is deliberately shown as an orthogonal attachment branch, not silently inserted as structural representation input.

---

## 4. Canonical execution DAG

### 4.1 DAG constitution

The registry stores nodes and typed dependency edges. The planner MUST:

- reject unknown stage IDs;
- reject cycles;
- verify required input/output type compatibility;
- resolve all required parent nodes before execution;
- preserve optional/forbidden dependency declarations;
- identify blocked descendants if any node is not authorised/unavailable;
- allow independent branches to execute concurrently only when deterministic ordering constraints do not require serialisation;
- never infer a missing scientific dependency.

### 4.2 Initial current-lawful graph

The exact adapter graph is implementation-bound at IROF-WP8 after source-surface tests. Design target:

```text
population_binding
  -> opt_a_observation_handoff
  -> c1
  -> revised_c2
  -> c2e_v0_2
  -> sri
      -> optional_normalization (only if selected RepresentationPack requires)
      -> comparability
      -> distance_similarity
      -> fdi_c2g
      -> family_evidence_stream

revised_c2/c2e occurrence identities
  -> occurrence_context (context-only by default)

eligible upstream population
  -> mcarb branch (only under MCARB authority; output is auxiliary evidence)

all meaningful nodes
  -> research_operations_evidence
  -> qa
```

The actual graph may omit a source recomputation stage when a profile binds an already sealed upstream artifact. A profile never changes scientific stage semantics.

### 4.3 Future nodes

Future C2P, revised C2.5, C3 AST, OPT-C and OPT-D are registered as ordinary StageSpecs. A new node requires no scheduler semantic change unless it introduces a genuinely new execution primitive, in which case that primitive receives its own version and QA rather than being hidden in the scientific adapter.

---

## 5. Population model

### 5.1 PopulationSpec

Required conceptual fields:

- `population_id`
- `population_mode`
- `population_schema_version`
- `source_release_id` / `source_manifest_hash` where applicable
- `instrument`
- `price_side`
- `clock_lattice`
- `start_time`, `end_time`
- `admissible_cutoff`
- `role`
- `expected_source_count`
- `source_adapter_id`
- `synthetic_fixture_id` or `generator_spec_id`
- `authority_binding_ids`
- `validation_access_state`
- `external_artifact_root_alias`
- `capacity_tier`
- `logical_hash`

### 5.2 Modes

IROF v0.1 proposes the following semantic modes, with an implementation-time crosswalk to existing programme vocabulary:

- `SYNTHETIC_FIXTURE`
- `SYNTHETIC_GENERATED`
- `SEALED_REAL_REPLAY`
- `TIME_GATED_REPLAY`
- `LIVE_PROSPECTIVE` — registered but not executable without future authority.

Mode is provenance/authority semantics; it does not create a different downstream engine.

### 5.3 Capacity tiers

- `MICRO`
- `SMALL`
- `MEDIUM`
- `LARGE`
- `LONG_HORIZON`

These are execution-governance labels only. Exact object counts, pair counts, configurations, bytes and resource budgets remain explicit fields. No scientific quality or confidence is implied by tier.

---

## 6. Pipeline profile model

PipelineProfile is a versioned hashable subgraph declaration containing:

- profile ID/version;
- included stage IDs;
- required terminal outputs;
- allowed optional branches;
- profile-level prerequisites;
- profile authority policy reference;
- default observability requirements;
- profile logical hash.

Initial proposed profiles:

- `C1_ONLY`
- `C2_ONLY`
- `C2_C2E`
- `STRUCTURAL_CORE`
- `FAMILY_RESEARCH`
- `FULL_DESCRIPTIVE`
- `FULL_DESCRIPTIVE_WITH_CONTEXT`

Future registry entries may add `OUTCOME_RESEARCH` and `FULL_ABCD` only after their stage contracts exist. Profiles do not redefine any stage.

---

## 7. Stage interface

### 7.1 StageSpec

Every registered stage declares:

- `stage_id`, `stage_version`, `stage_kind`;
- implementation identity/path;
- contract and schema identities/hashes;
- accepted input types and produced output types;
- required/optional/forbidden parent dependencies;
- required authority claims;
- required pack/config identities;
- deterministic contract (`EXACT`, `TOLERANCE_DECLARED`, `NONDETERMINISTIC_FORBIDDEN` for v0.1);
- execution backend;
- checkpoint capability (`NONE`, `STAGE`, `OPAQUE_SUBSTAGE`);
- cache capability and cache-scope declaration;
- resource estimator identity;
- external-artifact policy;
- QA check IDs;
- adapter identity;
- wrapper-mutation policy = `NO_SCIENTIFIC_MUTATION`.

### 7.2 StageAdapter

The generic adapter surface is intentionally narrow:

```text
preflight(invocation, resolved_parents, authority_context) -> StagePreflight
estimate(invocation, parent_metadata) -> ResourceEstimate | UNAVAILABLE
execute(invocation, input_refs, execution_context) -> StageResult
resume(invocation, input_refs, checkpoint_ref, execution_context) -> StageResult
verify(result) -> StageVerification
```

A stage owns scientific meaning and internal partition semantics. IROF owns dependency order, authority, physical execution lifecycle, generic artifact integrity and telemetry collection.

### 7.3 Wrapper prohibition

Adapters may translate transport/schema envelopes only where a frozen crosswalk authorises it. They may not repair, impute, reinterpret, select a winner, alter denominators or manufacture scientific fields.

---

## 8. Run identity

### 8.1 Three identities

1. **SemanticResearchRunID** — scientific/execution meaning independent of host/path/scheduling.
2. **ExecutionAttemptID** — one physical attempt of a semantic run.
3. **ArtifactLocation** — replaceable physical storage location.

### 8.2 Semantic identity material

As applicable:

- PopulationSpec logical identity and source manifest;
- PipelineProfile identity;
- stage contract/schema/implementation identities;
- boundary/representation/normalization/comparison/distance/family/sensitivity/context packs;
- chronology/first-valid policy;
- comparability-domain identity;
- code identity where the owning reproducibility contract requires it;
- parent semantic artifact hashes.

Explicitly excluded: hostname, absolute path, worker count unless a stage declares worker count scientific (not expected), scheduling order, restart count and physical artifact relocation.

### 8.3 Attempt identity

Attempt identity includes semantic run ID plus attempt sequence/nonce, environment fingerprint, resource envelope and physical execution metadata. Multiple attempts can implement one semantic run.

---

## 9. Authority model

### 9.1 AuthorityBinding

AuthorityBinding contains:

- binding ID;
- owning programme/gate;
- authority kind;
- subject population/stage/profile;
- exact scope;
- decision and status;
- source decision artifact/hash;
- valid/consumed state where tokenised;
- expiry/supersession if applicable.

### 9.2 Preflight rule

IROF must resolve authority **before protected source paths or objects are consumed** wherever existing OVC denial doctrine requires denial-before-resolution.

For every planned node:

```text
required authority
  vs current authority
  -> ALLOW | NOT_AUTHORISED | DEFERRED_BY_OPERATOR | BLOCKED_DEPENDENCY
```

If blocked, IROF emits an authority failure receipt naming:

- required/current authority;
- owner programme/gate;
- blocked node;
- blocked descendants;
- reusable completed ancestors;
- no-substitution assertion.

### 9.3 Current June consequence

At this baseline, an IROF full-descriptive real June run is **not authorised**. SRFD has a separately governed exact bounded June token, but C2E real replay remains denied. The planner must stop at the denied C2E node and may not call the SRFD token an integrated-pipeline grant.

---

## 10. Artifact model

ArtifactRef contains:

- stable artifact ID;
- logical hash;
- content SHA-256 where materialised;
- artifact type;
- owner stage/run;
- parent artifact IDs;
- semantic cache key if reusable;
- authority classification;
- lifecycle state;
- media/schema identity;
- size;
- portable location(s);
- created attempt ID;
- verification status.

Lifecycle states for IROF-managed artifacts:

- `STAGING`
- `COMPLETE`
- `QUARANTINED`
- `SUPERSEDED`

Research Operations catalogue availability remains a distinct axis and is not replaced.

---

## 11. Cache and immutable reuse semantics

### 11.1 SemanticCacheKey

The key MUST bind all meaning-relevant dependencies:

```text
stage_id/version
+ parent semantic artifact hashes
+ contract/schema/implementation identity
+ relevant pack/config IDs
+ PopulationSpec semantic identity where stage scope requires
+ chronology/comparability/context-role identities
+ code identity where frozen reproducibility requires
```

### 11.2 Reuse admission

Reuse is lawful only when:

- semantic key exact-matches;
- all parent hashes verify;
- contract/schema/pack identities match;
- output hash verifies;
- artifact state is COMPLETE;
- artifact is not quarantined or superseded for the requested semantics;
- owning stage permits reuse at this scope;
- authority still permits consuming the artifact.

A cache miss is an execution event, never scientific missingness.

### 11.3 Corruption

Hash mismatch moves the artifact to QUARANTINED and records `CACHE_ARTIFACT_HASH_MISMATCH`; IROF reruns only if execution remains lawful. It never silently repairs the artifact in place.

---

## 12. Checkpoint and restart

IROF coordinates three layers:

1. `RUN` — completed DAG nodes and pending nodes;
2. `STAGE` — stage-owned output/checkpoint boundary;
3. `OPAQUE_SUBSTAGE` — tile/partition checkpoint exposed by stage adapter.

IROF never invents scientific subpartitions. An opaque substage checkpoint must carry an owning stage checkpoint schema and verification function.

Restart sequence:

1. verify IntegratedRunManifest;
2. verify semantic run identity;
3. verify all reusable parent artifacts;
4. verify checkpoint content hashes;
5. quarantine corrupt completed output;
6. retain attempt/restart lineage;
7. execute only incomplete or invalid units;
8. compare final logical output with fresh-run expectation for deterministic stages.

Required synthetic proof: fresh run hash = repeated fresh run hash = resumed run hash for exact deterministic profiles.

---

## 13. Capacity architecture

IROF generalises SRFD capacity doctrine without weakening it.

Scheduler MAY:

- topologically order nodes;
- control concurrency;
- use verified cached ancestors;
- apply a stage-declared lawful partition plan;
- stop before/exactly at a resource limit;
- checkpoint;
- emit capacity states.

Scheduler MAY NOT:

- silently sample the population;
- drop methods/configurations;
- reduce sensitivity grids;
- change thresholds;
- alter scientific denominators;
- substitute a smaller profile;
- relabel a partial run as complete.

CapacityBudget binds wall/CPU/RSS/storage/concurrency constraints where available. `CAPACITY_EXCEEDED` preserves evidence and is not a scientific disposition.

---

## 14. Computational telemetry

### 14.1 StageExecutionReceipt

Each stage receipt records measurable fields and explicit `UNAVAILABLE` markers rather than fabricated metrics.

**Identity**: semantic run ID, attempt ID, stage ID/version, invocation ID.  
**Population**: input, eligible, output, not-evaluable, not-comparable, censored, residual counts where meaningful.  
**Time**: queue, wall, CPU/core-seconds, checkpoint, serialization, IO where measurable.  
**Memory**: peak RSS, declared working set, worker count.  
**Storage/IO**: bytes read/written, temporary/persistent bytes.  
**Work**: object/pair/tile/comparison/configuration counts plus typed extensions.  
**Throughput**: objects/pairs/bytes per second where meaningful.  
**Reuse**: hits/misses, reused artifacts, deterministically estimated avoided work/bytes.  
**Restart**: checkpoint/restart counts, recovered and repeated work units.  
**Result**: execution status, warnings, reason codes, capacity state, output artifact refs.

### 14.2 IntegratedRunReceipt

Aggregates total wall/CPU, max stage RSS, artifact growth, cumulative work counts, reuse and restart summaries, while retaining the complete per-stage receipt references. It must not sum mutually overlapping wall times and call the result makespan; diagnostic sums and actual end-to-end makespan are separately named.

---

## 15. Research Operations integration

IROF reuses rather than replaces:

- `canonical.py` for stable logical hashing conventions where compatible;
- `catalogue.py` for artifact identity/availability/dependencies;
- `qa.py` for non-mutating QA assertions and PASS/WARN/BLOCK/QUARANTINE;
- `storage.py` and approved path registry for governed locations;
- `read_model.py` for deterministic operator projection;
- existing Research Operations record/lifecycle services.

A complete IROF research run is projectable as a Research Operations evidence object containing:

```text
experiment_id
research_run_id
population_spec_ref
pipeline_manifest_ref
authority_manifest_ref
stage_manifest_refs
execution_receipt_refs
artifact_manifest_ref
QA_manifest_ref
result_manifest_ref
comparison/supersession lineage
```

Computation PASS proves contract-compliant computation, not a scientific claim.

---

## 16. QA and failure taxonomy

### 16.1 Execution states

IROF will crosswalk with existing vocabularies and avoid duplicate aliases. Required semantic concepts:

`READY`, `RUNNING`, `REUSED`, `COMPLETE`, `CAPACITY_EXCEEDED`, `FAILED`, `QUARANTINED`, `DEFERRED_BY_OPERATOR`, `NOT_AUTHORISED`.

### 16.2 Separate domains

**Scientific/domain output** examples: `NO_STABLE_FAMILY`, `NOT_EVALUABLE`, `NOT_COMPARABLE`, `AMBIGUOUS`, `RESIDUAL`.

**Execution failure** examples: `FAILED`, `CAPACITY_EXCEEDED`, `ARTIFACT_MISSING`, `HASH_MISMATCH`, `CHECKPOINT_INVALID`, `DEPENDENCY_UNAVAILABLE`.

**Authority failure** examples: `NOT_AUTHORISED`, `VALIDATION_DENIED`, `SELECTOR_DENIED`, `PROVIDER_INTAKE_DENIED`.

The domains MUST NOT be collapsed.

---

## 17. Synthetic/real convergence model

One scheduler and one StageSpec graph serves all modes. Synthetic and real populations principally differ in source/provenance and authority bindings.

Synthetic assurance must invoke the same typed adapters as real replay whenever the stage's public contract permits. Fixture-only adapters are allowed only for data generation or explicit adversarial stubs, never as substitutes for production-stage contracts.

A synthetic PASS is evidence of implementation conformance, not market validity and not real-run authority.

---

## 18. Extensibility model

A new stage is admitted through:

1. StageSpec registry entry;
2. typed adapter;
3. declared dependencies and output types;
4. authority binding class;
5. artifact/checkpoint/resource policy;
6. QA set;
7. profile update or new profile;
8. extension fixture.

Core scheduler changes are forbidden merely to teach IROF the scientific meaning of a new stage.

The v0.1 extension fixture will register a `FUTURE_TEST_STAGE` that transforms only opaque test payload metadata, proving scheduling/profile/receipt integration without scientific semantics.

---

## 19. Future C2P/C2.5/C3/OPT-C/OPT-D integration

- **C2P**: future StageSpec consumes only its separately frozen lawful inputs; OccurrenceContext is excluded from base identity unless C2P's own future contract permits a non-identity consumer role.
- **revised C2.5**: stage dependencies bind exact C2/C2E/C2P/context fields per its versioned dependency manifest; activation remains separate.
- **C3 AST**: adapter returns typed AST artifacts; IROF does not render meaning into the AST or choose a grammar.
- **OPT-C**: neutral outcome measurement consumes only lawful antecedent identities and temporal cutoffs; no outcome leakage upstream.
- **OPT-D**: evidence/validation profile remains authority-gated; Validation denial must occur before protected data path resolution.
- **MCARB**: auxiliary-representation stages form a branch. Their outputs become SRI inputs only when a separately governed RepresentationPack explicitly admits them.

---

## 20. Security and wrapper-leakage controls

Mandatory negative tests prove wrappers cannot:

- add market fields to inputs;
- infer absent scientific fields;
- leak future/outcome information;
- inject OccurrenceContext as `REPRESENTATION_INPUT` without a separately authorised pack;
- repair C2E episodes;
- alter missingness/denominators;
- silently fill nulls;
- collapse BID/ASK;
- alter clock/lattice;
- move first-valid time backward;
- select a best method/family;
- hide residual/null populations;
- consume Validation metadata/paths beyond current permission.

OccurrenceContext v0.1 consumer manifests already reject `REPRESENTATION_INPUT`; IROF adapters must preserve this behavior.

---

## 21. Storage boundaries

### Git

Contracts, schemas, registries, compact fixtures, manifests, hashes, compact receipts, QA, programme state, decisions and small benchmark summaries.

### External artifact root

Full state/episode/representation streams, pair/distance surfaces, reusable cache payloads, family payloads, large output sets and high-volume telemetry.

### R2

Only when a separately governed publication/evidence policy explicitly permits the specific artifact. IROF v0.1 has no new R2 write authority.

Physical path does not determine semantic identity.

---

## 22. CLI/API/read-model concepts

Existing `ovc` CLI routes into Research Operations, so IROF should extend the same command family rather than create a parallel executable. Proposed interface after implementation:

```text
ovc research run --profile <profile-id> --population <population-id>
ovc research preflight --profile <profile-id> --population <population-id>
ovc research resume --run <semantic-run-id> --attempt <attempt-id>
ovc research compare-runs --left <run-id> --right <run-id>
ovc research benchmark-scaling --ladder <ladder-id>
```

Exact subparser integration is frozen in IROF-WP1/WP8 after compatibility tests with current `research_operations.cli`.

Read-model surfaces expose run status, DAG, blocked authorities, stage telemetry, artifacts, QA, cache/restart state and comparison lineage. They are read-only in v0.1.

---

## 23. Adversarial fixture catalogue

Minimum v0.1 fixture families:

- `IROF-F01` deterministic micro complete chain;
- `IROF-F02` gap/missing parent propagation;
- `IROF-F03` C2 non-evaluable state;
- `IROF-F04` C2E birth/continuation/mutation;
- `IROF-F05` C2E censoring;
- `IROF-F06` split/merge/re-parent/conflict;
- `IROF-F07` SRI representation and comparability reject;
- `IROF-F08` exact-vs-tolerance comparison paths;
- `IROF-F09` residual family assignment;
- `IROF-F10` zero-family lawful result;
- `IROF-F11` ambiguous family assignment;
- `IROF-F12` OccurrenceContext context-only attachment;
- `IROF-F13` prohibited context representation injection;
- `IROF-F14` cache exact reuse;
- `IROF-F15` stale semantic-key cache miss;
- `IROF-F16` corrupted cache quarantine;
- `IROF-F17` forced stage checkpoint/resume;
- `IROF-F18` corrupt checkpoint fail-closed;
- `IROF-F19` worker/scheduling-order equivalence;
- `IROF-F20` capacity exceeded without scope mutation;
- `IROF-F21` C2E real replay denial before protected read;
- `IROF-F22` Validation denial before protected read;
- `IROF-F23` extension-stage registration without scheduler changes;
- `IROF-F24` Research Operations projection/QA non-mutation;
- `IROF-F25` MCARB branch unavailable/available authority paths.

---

## 24. Risks and unresolved questions

1. **Generic abstraction can accidentally erase scientific distinctions.** Mitigation: adapters are typed and stage-owned; IROF never normalises scientific statuses globally.
2. **Cache identity under-specification.** Mitigation: cache key construction is registry-driven, tested by semantic-change adversarial fixtures and defaults to recompute if uncertain.
3. **Cross-programme authority composition.** Mitigation: per-stage bindings and no implicit union of tokens. Current C2E/SRFD June asymmetry is a permanent regression fixture.
4. **Telemetry portability.** Some CPU/RSS/IO measures differ by OS. Metrics must be typed as `MEASURED` or `UNAVAILABLE`; unavailable values never become zero.
5. **Historical FSR divergence.** FSR demonstrated integration but used bespoke adapters and an older upper boundary. It is a fixture source, not canonical implementation.
6. **SRFD refactor risk.** Generic extraction could alter frozen SRFD v0.4 behavior. Required exact equivalence tests compare pre/post logical outputs and frozen rule-pack hash.
7. **Profile sprawl.** Profiles remain a small registry of named subgraphs, not a user-defined way to bypass authority.
8. **Long-horizon performance.** No production SLA is frozen in v0.1; multi-N measurement is required first.

No unresolved design question requires stopping before IROF-G0. Scientific/real-data authority questions remain outside IROF.

---

## 25. Definition of design completion

Design v0.1 is complete when:

- court record and open authority boundaries are reconciled;
- conform/generalise reuse plan is explicit;
- DAG, population/profile/stage/run identity contracts are specified;
- authority, cache, checkpoint, capacity, telemetry and storage semantics are defined;
- Research Operations integration is nonduplicative;
- synthetic/real use one execution architecture;
- current June asymmetry is represented fail-closed;
- extension mechanism is stage-registry based;
- implementation packets and acceptance tests can be written without scientific-design invention.

This specification satisfies those conditions and is ready for IROF-G0 operator review.

---

# Appendix A — Object catalogue

| Object | Purpose | Authority effect |
|---|---|---|
| PopulationSpec | immutable population/provenance/execution scope | NONE |
| PipelineProfile | versioned DAG subgraph | NONE |
| StageSpec | stage registration contract | NONE |
| StageInvocation | resolved one-run stage request | NONE |
| StageDependency | typed DAG edge | NONE |
| AuthorityBinding | reference to existing authority | NONE / enforcement only |
| ResearchRunSpec | requested semantic experiment | NONE |
| IntegratedRunManifest | frozen planned run | NONE |
| StageExecutionReceipt | stage execution evidence | NONE |
| IntegratedRunReceipt | whole-run evidence | NONE |
| ArtifactRef | immutable artifact identity/location metadata | NONE |
| SemanticCacheKey | reuse identity | NONE |
| CheckpointRecord | verified restart boundary | NONE |
| RestartLedger | attempt/recovery lineage | NONE |
| CapacityBudget | execution resource envelope | NONE |
| CapacityReceipt | measured/estimated capacity evidence | NONE |
| RunFailure | typed execution/authority failure | NONE |
| RunComparisonRecord | comparison of two run identities/results | NONE |

# Appendix B — Schema set proposed for WP1

- `population_spec/v0.1`
- `pipeline_profile/v0.1`
- `stage_spec/v0.1`
- `stage_invocation/v0.1`
- `authority_binding/v0.1`
- `research_run_spec/v0.1`
- `integrated_run_manifest/v0.1`
- `artifact_ref/v0.1`
- `semantic_cache_key/v0.1`
- `checkpoint_record/v0.1`
- `restart_ledger/v0.1`
- `capacity_budget/v0.1`
- `capacity_receipt/v0.1`
- `stage_execution_receipt/v0.1`
- `integrated_run_receipt/v0.1`
- `run_failure/v0.1`
- `run_comparison_record/v0.1`

# Appendix C — Status and reason-code domains

**Execution:** `READY`, `RUNNING`, `REUSED`, `COMPLETE`, `CAPACITY_EXCEEDED`, `FAILED`, `QUARANTINED`.  
**Authority:** `AUTHORISED`, `NOT_AUTHORISED`, `DEFERRED_BY_OPERATOR`.  
**Artifact:** `STAGING`, `COMPLETE`, `QUARANTINED`, `SUPERSEDED`.  
**Scientific values:** preserved verbatim from stage-owning registries; IROF does not own a global scientific-result enum.

Initial IROF reason-code families:

- `IROF_AUTH_*`
- `IROF_DEP_*`
- `IROF_CACHE_*`
- `IROF_CHECKPOINT_*`
- `IROF_CAPACITY_*`
- `IROF_ARTIFACT_*`
- `IROF_TELEMETRY_*`
- `IROF_ADAPTER_*`
- `IROF_PROFILE_*`
- `IROF_QA_*`

# Appendix D — Stage-registration template

```yaml
stage_id: OVC.STAGE.EXAMPLE
stage_version: 0.1
stage_kind: DERIVED_RESEARCH
implementation_identity: module:function
contract_identity: contract-id
schema_identity: schema-id
input_types: [TypeA]
output_types: [TypeB]
required_parents: [OVC.STAGE.PARENT]
optional_parents: []
forbidden_parents: []
authority_requirements: [AUTHORITY_ID]
pack_requirements: []
deterministic_mode: EXACT
checkpoint_capability: STAGE
cache_capability: true
cache_scope: POPULATION_SCOPED
resource_estimator: estimator-id
external_artifact_policy: EXTERNAL_IF_LARGE
qa_requirements: [IROF-QA-...]
adapter_identity: adapter-id
wrapper_policy: NO_SCIENTIFIC_MUTATION
```

# Appendix E — Population examples

Synthetic fixture:

```yaml
population_id: IROF.POP.SYNTH.MICRO.001
population_mode: SYNTHETIC_FIXTURE
instrument: GBPUSD
price_side: [BID, ASK]
clock_lattice: [15M, 2H_A_L]
role: NON_EVIDENTIARY_SYNTHETIC
capacity_tier: MICRO
validation_access_state: DENIED
```

Real replay request (preflight only unless separately authorised):

```yaml
population_id: IROF.POP.JUNE.2026.REQUEST.001
population_mode: SEALED_REAL_REPLAY
source_release_id: RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1
instrument: GBPUSD
role: REPLAY_REQUEST
capacity_tier: LARGE
validation_access_state: LOCKED_UNCONSUMED
authority_binding_ids: [exact-owning-programme-bindings]
```

# Appendix F — Pipeline profile example

```yaml
profile_id: IROF.PROFILE.FULL_DESCRIPTIVE.v0.1
stages:
  - POPULATION_BINDING
  - OPT_A_HANDOFF
  - C1
  - REVISED_C2
  - C2E_V0_2
  - SRI
  - COMPARABILITY
  - DISTANCE_SIMILARITY
  - FDI_C2G
  - FAMILY_EVIDENCE_STREAM
  - RESEARCH_OPERATIONS_EVIDENCE
  - QA
optional_branches:
  - OCCURRENCE_CONTEXT
  - MCARB
```

# Appendix G — IntegratedRunManifest example

```json
{
  "schema": "ovc-irof-integrated-run-manifest/v0.1",
  "semantic_run_id": "IROF.RUN.<hash>",
  "population_spec_hash": "<hash>",
  "pipeline_profile_hash": "<hash>",
  "authority_binding_hashes": ["<hash>"],
  "planned_stage_invocations": ["<id>"],
  "planned_edges": [["parent", "child"]],
  "semantic_inputs_hash": "<hash>",
  "physical_location_in_identity": false,
  "hostname_in_identity": false,
  "authority_effect": "NONE"
}
```

# Appendix H — Authority matrix

| Action | IROF-G0 requested? | Owning authority |
|---|---:|---|
| contracts/schemas/registries | YES | IROF-G0 |
| deterministic orchestration code | YES | IROF-G0 |
| synthetic fixtures/runs | YES | IROF-G0 |
| cache/checkpoint/capacity/telemetry | YES | IROF-G0 |
| read-only stage adapters | YES | IROF-G0 + source-stage contracts |
| Research Operations read/evidence integration | YES | IROF-G0 + existing RO authority |
| provider intake | NO | OPT-A/provider programme |
| real C2E June replay | NO | C2E owning gate |
| SRFD June run | NO new authority | SRFD own token/gate only |
| selector activation/replacement | NO | owning selector gate |
| Validation consumption | NO | Validation gate |
| representation/family promotion | NO | owning scientific gate |
| C2E activation | NO | C2E activation gate |
| C2P/C2.5/C3 semantics/activation | NO | future owning programmes |
| R2/canonical publication | NO | publication gate |
| probability/risk/exposure/execution | NO | future E-H authority |

# Appendix I — Architecture crosswalk

| Existing component | IROF treatment |
|---|---|
| SRFD `orchestration.py` | generalise generic DAG/checkpoint patterns; preserve SRFD fixture behavior through equivalence tests |
| SRFD `scheduler.py` | extract generic topology/resource planning concepts; stage-specific method completeness remains SRFD-owned |
| SRFD `semantic_cache.py` | generalise key/quarantine/complete-ledger primitives; keep SRFD cache compatibility adapter |
| SRFD capacity modules | reuse environment/IO measurement and no-scope-change doctrine; generic metrics move to IROF, SRFD scientific work estimator stays SRFD-owned |
| SFC `replay.py` | reuse manifest/checkpoint/capacity/interlock invariants via adapter/tests |
| C2E v0.2 | adapter to existing stream/checkpoint/assurance surfaces; no episode repair |
| Research Operations | consume canonical/catalogue/QA/storage/read-model services; do not duplicate evidence store |
| OccurrenceContext | register context branch; preserve context-only consumer firewall |
| FSR PR #418 | convert scenarios into golden tests; do not merge bespoke historical implementation |
| MCARB | future/current branch adapter only under MCARB authority; no automatic representation-input role |

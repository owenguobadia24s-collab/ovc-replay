# OVC Integrated Research Orchestration Framework
## Implementation Plan v0.1

**Programme:** OVC-IROF-v0.1  
**Document ID:** OVC-IROF-IMPLEMENTATION-PLAN-0.1  
**Governing design:** OVC-IROF-DESIGN-SPEC-0.1  
**Repository:** `owenguobadia24s-collab/ovc-replay`  
**Execution baseline:** latest lawful `main`, initially pinned at `ffefd1ee3d7ee664f2a94f74d05993d6e711a149`; re-resolve at IROF-WP0 after G0 PASS  
**Status:** IMPLEMENTATION PLAN COMPLETE / GATE_READY / NO CODE AUTHORITY UNTIL IROF-G0  
**First gate:** IROF-G0 — DESIGN + IMPLEMENTATION PLAN RATIFICATION

> **Authority notice.** IROF-G0 is the sole planned operator-required entry gate for the engineering programme. PASS authorises only bounded cross-cutting contracts, schemas, registries, deterministic orchestration code, synthetic fixtures/runs, cache/checkpoint/capacity/telemetry infrastructure, read-only adapters, Research Operations integration, tests and QA. It does not authorise any separately reserved real market run, provider intake, selector change, C2E activation, scientific promotion, Validation use, publication, future C2P/C2.5/C3 semantics, or exposure authority.

---

## 0. Executive implementation decision

### 0.1 Decision

Implement IROF as a new cross-cutting sibling package, proposed initially at:

```text
src/ovc/research_orchestration/
    __init__.py
    models.py
    serialization.py
    registry.py
    population.py
    profiles.py
    dag.py
    planner.py
    authority.py
    adapters.py
    cache.py
    checkpoint.py
    capacity.py
    telemetry.py
    evidence.py
    cli.py
```

Keep the package deliberately flatter than the conceptual design tree because current `ovc` packages are predominantly flat modules. Split into subpackages only if WP0 demonstrates a concrete maintenance benefit.

Repository control artifacts are proposed under:

```text
contracts/research_orchestration/
schemas/research_orchestration/
registries/research_orchestration/
registries/implementation/irof/
fixtures/research_orchestration/
tests/research_orchestration/
docs/releases/irof-v0-1/
```

The implementation MUST conform existing SRFD/SFC/C2E behavior rather than move frozen scientific logic wholesale. Generic execution primitives may be extracted or wrapped only with exact equivalence proof.

### 0.2 Programme strategy

1. Freeze generic identities/contracts before refactoring execution primitives.
2. Build DAG planning and authority preflight before any stage execution integration.
3. Generalise cache/checkpoint/capacity primitives with compatibility fixtures.
4. Integrate Research Operations evidence and QA before current-stage adapters.
5. Register current lawful adapters and profiles.
6. Prove a current-boundary synthetic full-chain run.
7. Measure a deterministic multi-N synthetic performance ladder.
8. End with real-population dry-run evidence and an extension-stage proof.

No packet may use implementation success to change scientific authority.

---

## 1. Baseline and source reconciliation

### 1.1 Baseline court record

At plan creation:

- `main = ffefd1ee3d7ee664f2a94f74d05993d6e711a149`.
- SFC is completed/preserved.
- C2E v0.2 real replay remains denied/deferred; active C2E and active boundary pack remain NONE.
- OccurrenceContext v0.1 is completed and nonstructural.
- C2 v2 Discovery is active; Development is reference-only; Validation is locked/unconsumed.
- SRFD has one separately governed exact bounded June token currently unconsumed; IROF receives no right to consume it.
- PR #479 is current blocker evidence for C2E June replay.
- PR #433 is current SRFD capacity evidence.
- PR #418 is a historical draft synthetic full-stack rehearsal; scenarios may be ported, code must not be promoted by merge.

IROF-WP0 MUST re-resolve this state because authority can move before operator approval.

### 1.2 Existing primitives to reuse or conform

| Source | Primitive | IROF action |
|---|---|---|
| `opt_b/srfd/orchestration.py` | deterministic stage receipts/checkpoint/hash | generalise execution-neutral pieces; exact fixture equivalence |
| `opt_b/srfd/scheduler.py` | topology/resource contracts/capacity states | generalise topology/resource layer; leave family-method completeness SRFD-owned |
| `opt_b/srfd/semantic_cache.py` | semantic keys/corruption quarantine/tile ledger | extract generic protocol; preserve SRFD compatibility |
| `opt_b/srfd/capacity*.py` | environment, CPU/RSS/storage/IO measurement | reuse observability infrastructure; do not move scientific estimator semantics |
| `opt_b/sfc/replay.py` | replay manifest/checkpoint/resume/capacity guard/interlock | adapter and invariant tests |
| `opt_b/c2e_v2/*` | stream manifest/checkpoint/restart/synthetic assurance | adapter only; no episode repair |
| `context/occurrence_context/*` | context attachment/consumer-role firewall | direct stage adapter, context-only default |
| `research_operations/*` | canonical hash, catalogue, QA, storage, read model | first-class integration, no duplicate evidence store |
| FSR PR #418 | synthetic end-to-end scenarios | adversarial/golden fixture source only |

---

## 2. Programme state and gate model

Machine-readable IROF programme state MUST track:

```text
packet_id
plan_id
plan_version
status
prerequisites
authority_required
authority_delta
baseline_commit
branch
candidate_commit
tests
qa_packet
decision_record
merge_commit
blockers
next_packet
```

Allowed packet states follow OVC programme doctrine: `PLANNED`, `READY`, `RUNNING`, `IMPLEMENTED`, `QA_REVIEW`, `GATE_READY`, `APPROVED`, `BLOCKED`, `QUARANTINED`, `SUPERSEDED`, `COMPLETED`.

### 2.1 Gate classification

- **IROF-G0** — OPERATOR REQUIRED: ratify design/plan and exact bounded implementation authority.
- **IROF-G1...G11** — AUTO-RATIFIABLE only when the packet delta is contracts/schemas/registries/deterministic code/fixtures/local synthetic execution/telemetry/read-only integration and all checks pass.
- Any attempted separately reserved action is **not an IROF gate**. The planner produces an authority failure/preflight packet and stops that action under the owning programme.

---

# 3. IROF-WP0 — Bootstrap, court-record preflight and conformance inventory

**Gate:** IROF-G1  
**Prerequisite:** IROF-G0 PASS; latest lawful main verified.

### Authority delta

Repository-local programme bootstrap, source inspection, documentation, compatibility inventory and tests only.

### Proposed files

- `registries/implementation/irof/OVC_IROF_STATE_v0_2.json`
- `registries/implementation/irof/CURRENT_STATE_POINTER.json`
- `docs/releases/irof-v0-1/irof-wp0/IROF_WP0_COURT_RECORD.json`
- `docs/releases/irof-v0-1/irof-wp0/IROF_WP0_CONFORMANCE_INVENTORY.json`
- `docs/releases/irof-v0-1/irof-wp0/IROF_WP0_OPEN_PR_DISPOSITION.md`
- `tests/research_orchestration/test_wp0_court_record.py`

### Tasks

1. Re-pin main, open PRs, branches and programme pointers.
2. Resolve exact current authority for OPT-A/C1/C2/C2E/SFC/SRFD/OccurrenceContext/MCARB/Validation.
3. Hash all existing reusable orchestration primitives.
4. Classify each primitive: `REUSE_DIRECT`, `GENERALISE_WITH_EQUIVALENCE`, `ADAPTER_ONLY`, `HISTORICAL_FIXTURE_ONLY`, `FORBIDDEN`.
5. Confirm no pre-existing IROF package/registry conflicts.
6. Freeze source-code and fixture baselines needed for later equivalence tests.

### Tests / QA

- source paths exist and hashes resolve;
- no authority state inferred from chat;
- every current stage has an owner programme;
- open PR classification does not treat proposal branches as authority;
- Validation remains denial-before-resolution.

### Acceptance

PASS only if repository state is unambiguous and no governing conflict exists. If a source package moved materially after G0, update the conformance inventory without broadening scope.

### Rollback

Delete/supersede only the WP0 derived inventory/state pointer; preserve all inspected source records.

### Next

IROF-WP1.

---

# 4. IROF-WP1 — Core contracts, schemas, registries, population/profile identity

**Gate:** IROF-G2  
**Prerequisite:** IROF-G1 PASS.

### Authority delta

Typed inactive orchestration contracts only.

### Proposed implementation files

- `src/ovc/research_orchestration/models.py`
- `src/ovc/research_orchestration/serialization.py`
- `src/ovc/research_orchestration/registry.py`
- `src/ovc/research_orchestration/population.py`
- `src/ovc/research_orchestration/profiles.py`
- `contracts/research_orchestration/IROF_CORE_CONTRACT_v0_1.md`
- `schemas/research_orchestration/*.json`
- `registries/research_orchestration/STATUS_REASON_CODE_REGISTRY_v0_1.yaml`
- `registries/research_orchestration/POPULATION_MODE_REGISTRY_v0_1.yaml`
- `registries/research_orchestration/PIPELINE_PROFILE_REGISTRY_v0_1.yaml`
- `tests/research_orchestration/test_wp1_models_identity.py`

### Required object contracts

PopulationSpec, PipelineProfile, StageSpec, StageInvocation, StageDependency, AuthorityBinding, ResearchRunSpec, IntegratedRunManifest, StageExecutionReceipt, IntegratedRunReceipt, ArtifactRef, SemanticCacheKey, CheckpointRecord, RestartLedger, CapacityBudget, CapacityReceipt, RunFailure and RunComparisonRecord.

### Identity tests

- host/path relocation does not change semantic identity;
- worker count/scheduling/restart count do not change semantic identity unless explicitly declared stage-semantic;
- pack/config change changes the appropriate stage/run identity;
- physical artifact location can change without semantic identity change;
- duplicate stage/profile IDs fail closed;
- scientific result statuses are not normalised into execution statuses.

### Fixtures

Micro PopulationSpec examples for synthetic fixture/generated/replay request; profile subgraphs; authority-binding examples; invalid identity examples.

### Acceptance

All schemas validate, logical hashing is deterministic, and no object grants authority by construction.

### Rollback

Remove inactive IROF contracts/registries/package files; no source-stage behavior touched.

### Next

IROF-WP2.

---

# 5. IROF-WP2 — Stage adapters, canonical DAG and dependency planner

**Gate:** IROF-G3  
**Prerequisite:** IROF-G2 PASS.

### Authority delta

Deterministic DAG planning and inert adapter protocol.

### Proposed files

- `src/ovc/research_orchestration/dag.py`
- `src/ovc/research_orchestration/planner.py`
- `src/ovc/research_orchestration/adapters.py`
- `contracts/research_orchestration/STAGE_ADAPTER_CONTRACT_v0_1.md`
- `registries/research_orchestration/STAGE_REGISTRY_v0_1.yaml`
- `fixtures/research_orchestration/dag/*.json`
- `tests/research_orchestration/test_wp2_dag_planner.py`
- `tests/research_orchestration/test_wp2_adapter_firewall.py`

### Tasks

- deterministic topological planner;
- required/optional/forbidden dependency validation;
- typed input/output compatibility;
- blocked-descendant calculation;
- profile-as-subgraph resolution;
- adapter protocol with preflight/estimate/execute/resume/verify hooks;
- no scientific payload inspection in generic planner beyond declared envelope fields.

### Adversarial tests

cycles, missing parent, forbidden edge, output/input type mismatch, hidden extra dependency, wrapper-mutated field, parent-order shuffle.

### Acceptance

Equivalent DAG declarations produce identical canonical plans independent of registration order. A hypothetical extension stage can be registered in fixtures without modifying scheduler code.

### Rollback

Remove IROF planner/adapter code only.

### Next

IROF-WP3.

---

# 6. IROF-WP3 — Authority resolver and population binding

**Gate:** IROF-G4  
**Prerequisite:** IROF-G3 PASS.

### Authority delta

Read-only authority enforcement and dry-run population resolution. No new authority.

### Proposed files

- `src/ovc/research_orchestration/authority.py`
- updates to `population.py` / `planner.py`
- `registries/research_orchestration/AUTHORITY_REQUIREMENT_REGISTRY_v0_1.yaml`
- `fixtures/research_orchestration/authority/*.json`
- `tests/research_orchestration/test_wp3_authority.py`
- `tests/research_orchestration/test_wp3_validation_denial.py`

### Tasks

- bind authority owner programme/gate to StageSpec;
- denial-before-protected-resolution contract;
- token scope/consumption awareness without consuming owner tokens;
- real-vs-synthetic source adapter policy;
- exact blocked-node/descendant receipt;
- reusable ancestor reporting;
- no silent profile degradation or synthetic substitution.

### Mandatory current regression

A `FULL_DESCRIPTIVE` June real preflight MUST fail at the current C2E real replay boundary even while separately reporting that SRFD has its own exact bounded June authority. It MUST NOT consume the SRFD token.

### Acceptance

All reserved operations fail closed with owning gate and no protected data consumption. Synthetic fixture profiles remain executable under IROF synthetic authority.

### Rollback

Authority resolver removal; no owner authority files modified.

### Next

IROF-WP4.

---

# 7. IROF-WP4 — Semantic artifact cache and immutable reuse

**Gate:** IROF-G5  
**Prerequisite:** IROF-G4 PASS.

### Authority delta

Execution optimisation only; no scientific effect.

### Proposed files

- `src/ovc/research_orchestration/cache.py`
- `contracts/research_orchestration/SEMANTIC_CACHE_CONTRACT_v0_1.md`
- cache schemas/fixtures;
- `tests/research_orchestration/test_wp4_cache.py`
- SRFD compatibility tests under `tests/opt_b/srfd/` only if needed to prove unchanged output.

### Refactor/reuse rule

Generalise SRFD semantic cache key/quarantine patterns. Do not delete or rewrite the SRFD public behavior until exact compatibility tests pass; use a compatibility wrapper first.

### Tests

- exact hit;
- semantic field change -> miss;
- path relocation -> hit;
- corrupt payload -> quarantine + miss;
- SUPERSEDED/QUARANTINED artifact -> no reuse;
- parent hash mismatch -> no reuse;
- cache hit/miss counters do not affect scientific hash;
- cached and recomputed outputs equal.

### Acceptance

No stale semantic reuse; bytes/work avoided are only reported when deterministically measurable.

### Rollback

Disable IROF cache adapter and revert to compute; scientific outputs unchanged.

### Next

IROF-WP5.

---

# 8. IROF-WP5 — Checkpoint/restart and failure recovery

**Gate:** IROF-G6  
**Prerequisite:** IROF-G5 PASS.

### Authority delta

Deterministic execution recovery only.

### Proposed files

- `src/ovc/research_orchestration/checkpoint.py`
- `contracts/research_orchestration/CHECKPOINT_RESTART_CONTRACT_v0_1.md`
- checkpoint schemas/fixtures;
- `tests/research_orchestration/test_wp5_checkpoint_restart.py`
- compatibility tests for SFC/SRFD/C2E checkpoint primitives.

### Tasks

- run-level checkpoint manifest;
- stage completion ledger;
- opaque stage-owned substage checkpoint references;
- attempt/restart lineage;
- corruption quarantine;
- verified resume planner;
- no incomplete-as-complete state.

### Acceptance proof

For exact deterministic fixture stages:

```text
fresh logical hash == repeated fresh logical hash == resumed logical hash
```

Corrupted checkpoint must fail closed or rerun the affected lawful unit; it cannot be silently repaired.

### Rollback

Restart from fresh run using unchanged stage contracts.

### Next

IROF-WP6.

---

# 9. IROF-WP6 — Capacity scheduler and computational telemetry

**Gate:** IROF-G7  
**Prerequisite:** IROF-G6 PASS.

### Authority delta

Resource scheduling/measurement only; no experiment mutation.

### Proposed files

- `src/ovc/research_orchestration/capacity.py`
- `src/ovc/research_orchestration/telemetry.py`
- `contracts/research_orchestration/CAPACITY_AND_TELEMETRY_CONTRACT_v0_1.md`
- telemetry/capacity schemas;
- `registries/research_orchestration/TELEMETRY_METRIC_REGISTRY_v0_1.yaml`
- `fixtures/research_orchestration/capacity/*.json`
- `tests/research_orchestration/test_wp6_capacity.py`
- `tests/research_orchestration/test_wp6_telemetry.py`

### Generalisation

Reuse SRFD environment/IO profiling and topology/resource-contract patterns. Retain SRFD-specific method/config completeness rules inside SRFD. Generic IROF owns resource envelopes, measurable runtime/CPU/RSS/IO/work/reuse/restart receipts and DAG-level scheduling.

### Mandatory prohibitions

No sampling, method dropping, grid reduction, threshold change, denominator change or profile substitution on capacity failure.

### Metrics

At minimum support typed availability for wall time, CPU time/core-seconds, peak RSS, worker count, bytes read/written, persistent/temp bytes, object/pair/tile/config counts, throughput, cache/restart counts, warnings/reasons and capacity status.

### Acceptance

Forced capacity failure returns `CAPACITY_EXCEEDED` with exact preserved experiment identity and `scientific_effect=NONE`. Telemetry measurement itself must not change semantic output hashes.

### Rollback

Fall back to serial/default resource execution; scientific adapters unchanged.

### Next

IROF-WP7.

---

# 10. IROF-WP7 — Research Operations, QA and artifact-catalogue integration

**Gate:** IROF-G8  
**Prerequisite:** IROF-G7 PASS.

### Authority delta

Append-only/read-only evidence integration within existing Research Operations authority.

### Proposed files

- `src/ovc/research_orchestration/evidence.py`
- `contracts/research_orchestration/RESEARCH_OPERATIONS_INTEGRATION_v0_1.md`
- `tests/research_orchestration/test_wp7_research_operations.py`
- minimal updates to Research Operations read-model/CLI adapter registries only where existing extension points require.

### Tasks

- map IROF ArtifactRef to Research Operations artifact declarations;
- register run/stage receipts as evidence refs;
- invoke existing non-mutating QARunner;
- project run DAG/status/telemetry into deterministic read model;
- record incidents for corruption/capacity/authority failures without converting them into market claims;
- preserve negative/null scientific results as results, not incidents.

### Acceptance

Artifact catalogue re-verifies hashes; QA cannot mutate target; same run evidence rebuilds to same logical read model; large artifacts stay external.

### Rollback

Remove IROF read projection; underlying run artifacts remain addressable.

### Next

IROF-WP8.

---

# 11. IROF-WP8 — Current-layer adapters and canonical profiles

**Gate:** IROF-G9  
**Prerequisite:** IROF-G8 PASS; all source stage contracts still present.

### Authority delta

Read-only/synthetic invocation adapters to currently lawful stage capabilities. No source-stage authority change.

### Proposed files

- `src/ovc/research_orchestration/stage_adapters.py` or a small `adapters/` subpackage if WP0 proves justified;
- `registries/research_orchestration/STAGE_REGISTRY_v0_2.yaml`;
- `registries/research_orchestration/PIPELINE_PROFILE_REGISTRY_v0_2.yaml`;
- adapter fixtures and source-surface crosswalk;
- `tests/research_orchestration/test_wp8_current_adapters.py`.

### Required current adapters, subject to WP0 availability

- source/OPT-A fixture or sealed-handoff binding;
- C1;
- revised C2;
- C2E v0.2 synthetic/inactive handoff;
- OccurrenceContext context-only branch;
- SRI;
- normalization only when selected pack requires;
- comparability;
- distance/similarity;
- FDI/C2G;
- FamilyEvidenceStream;
- Research Operations/QA terminal evidence;
- MCARB branch registration as unavailable/authority-gated if its current stage contract is not executable.

### Equivalence requirements

- SRFD frozen v0.4 scientific rule pack hash remains exact;
- adapter wrapping/unwrapping preserves scientific numerators/denominators/statuses/reason codes;
- C2E episodes are never repaired or reconstructed;
- OccurrenceContext `REPRESENTATION_INPUT` is rejected absent an explicitly authorised representation pack.

### Profiles frozen here

At least `C1_ONLY`, `C2_ONLY`, `C2_C2E`, `STRUCTURAL_CORE`, `FAMILY_RESEARCH`, `FULL_DESCRIPTIVE`, `FULL_DESCRIPTIVE_WITH_CONTEXT`, adjusted only if WP0 source contracts require more precise names/dependencies.

### Acceptance

Source-surface compatibility PASS; no forbidden legacy fallback; all adapter authority effects NONE.

### Rollback

Unregister IROF adapters/profiles; source packages untouched.

### Next

IROF-WP9.

---

# 12. IROF-WP9 — Golden synthetic full-chain integration and determinism assurance

**Gate:** IROF-G10  
**Prerequisite:** IROF-G9 PASS.

### Authority delta

Local synthetic execution only.

### Proposed files

- `fixtures/research_orchestration/golden_v0_1/*`
- `tests/research_orchestration/test_wp9_full_chain.py`
- `tests/research_orchestration/test_wp9_restart_cache_order.py`
- compact receipts under `docs/releases/irof-v0-1/irof-wp9/`.

### Fixture content

Ordinary observations, gaps, missing parents, non-evaluable states, transitions, C2E birth/continuation/mutation, censoring, split, merge, re-parenting, conflicts, representations, comparability rejection, exact/tolerance comparison, residual/zero-family/ambiguous assignments, OccurrenceContext attachment, cache reuse, forced checkpoint/restart, corrupted cache and worker-order permutations.

### Historical FSR treatment

Port useful scenarios from PR #418 into current contracts. Do not import FSR bespoke upper-layer assumptions or merge the draft branch.

### Required proof

A single synthetic population reaches the furthest currently lawful descriptive evidence surface. For exact deterministic nodes:

```text
fresh == repeated fresh == resumed == alternate scheduling order
```

Scientific null outputs remain successful computation where lawful.

### Acceptance

All golden checks PASS, no reserved authority touched, Research Operations evidence rebuild PASS.

### Rollback

Fixtures/derived synthetic artifacts only.

### Next

IROF-WP10.

---

# 13. IROF-WP10 — Multi-N performance and capacity characterization

**Gate:** IROF-G11  
**Prerequisite:** IROF-G10 PASS.

### Authority delta

Synthetic performance measurement only.

### Proposed files

- `fixtures/research_orchestration/scaling_ladder_v0_1.yaml`
- `src/ovc/research_orchestration/benchmark.py` only if needed; otherwise CLI invokes existing runner;
- `tests/research_orchestration/test_wp10_scaling_ladder.py`;
- compact measured summaries under `docs/releases/irof-v0-1/irof-wp10/`;
- large raw telemetry under external artifact root.

### Ladder

At least MICRO plus three increasing synthetic N values chosen after WP6 measured calibration. Preserve identical scientific packs across the ladder where structurally possible. Exact N values are engineering measurements, not scientific ranks.

### Required outputs

Per-stage and whole-run:

- wall/CPU/core-seconds;
- peak RSS where available;
- artifact bytes;
- work counts;
- pair/family/config growth;
- cache/no-cache comparison;
- checkpoint overhead;
- restart recovery cost;
- parallelism efficiency where measurable;
- predicted vs observed resource envelope.

Classify empirical shape as `APPROX_LINEAR_OBSERVED`, `SUPER_LINEAR_OBSERVED`, `KNOWN_QUADRATIC_WORK_COUNT`, `FIXED_OVERHEAD_DOMINANT`, or `UNRESOLVED`, without inventing production SLA.

### Acceptance

Measured evidence reproducible enough to identify bottlenecks; no optimization changes scientific output. Any candidate optimized implementation requires equivalence identity and proof.

### Rollback

Discard/supersede synthetic performance artifacts; no scientific state changed.

### Next

IROF-WP11.

---

# 14. IROF-WP11 — Real-population preflight, extension proof and closeout

**Terminal gate:** IROF-G12 — AUTO-RATIFIABLE only if authority delta is programme completion/inactive infrastructure availability; otherwise stop at the external owning gate, not IROF.  
**Prerequisite:** IROF-G11 PASS.

### Authority delta

Read-only preflight + synthetic extension proof + programme closeout. No real run authority.

### Proposed files

- real-preflight compact packet under `docs/releases/irof-v0-1/irof-wp11/`;
- extension fixture StageSpec/adapter under fixtures/tests;
- terminal state `registries/implementation/irof/OVC_IROF_STATE_v0_FINAL.json`;
- terminal pointer and completion receipt.

### Real preflight

Resolve requested June population, source release, DAG, authorities, cache, workload, space, pair/config estimates and blocked nodes. Do not consume protected data or owner tokens merely to preflight.

If C2E remains denied, expected classification is:

`REAL_RUN_READY_BUT_NOT_AUTHORISED` as an evidence disposition with execution status `NOT_AUTHORISED`, naming the owning C2E gate and all blocked descendants.

If repository authority has changed by then, IROF may report that fact but MUST NOT execute a separately reserved real run unless the owning decision explicitly authorises invocation through IROF.

### Extension proof

Register and execute a synthetic metadata-only future test stage via StageSpec + adapter + profile update without modifying core scheduler semantics.

### Closeout acceptance

Terminal report includes:

- exact main SHA;
- implemented profiles/stages;
- micro/larger synthetic results;
- repeated/restart/cache equivalence;
- capacity-failure result;
- authority-failure result;
- current descriptive E2E result;
- multi-N telemetry summary;
- current real-run readiness and exact blocked authorities;
- future registrations not yet admitted;
- recommended next programme.

Target state: `IMPLEMENTED / INACTIVE_INFRASTRUCTURE_AVAILABLE`.

### Rollback

Disable/remove IROF profile registrations and CLI route. Preserve source-stage outputs and Research Operations evidence; no source programme is rewritten.

---

## 15. Test and QA programme

### 15.1 Core test families

- schema/serialization canonicality;
- run identity invariance and semantic sensitivity;
- DAG determinism/cycle/missing dependency;
- adapter leakage firewalls;
- authority denial-before-resolution;
- cache reuse/corruption/quarantine;
- checkpoint fresh-vs-resume equivalence;
- capacity no-scope-change;
- telemetry availability and aggregation correctness;
- Research Operations QA non-mutation;
- source-adapter scientific equivalence;
- full-chain synthetic golden;
- multi-N scaling;
- real-run preflight;
- extension registration.

### 15.2 Repository-wide assurance

Every packet after code starts runs targeted tests plus the repository's established complete test/OVC assurance/compatibility/merge-readiness suites at exact PR head. Base movement requires rerun before merge.

### 15.3 Blocking QA conditions

- scientific output drift in a claimed equivalent adapter/refactor;
- hidden sampling/grid reduction;
- stale cache acceptance;
- authority union/bypass;
- protected Validation/provider path resolution before authority;
- context structural injection;
- C2E episode repair;
- first-valid/clock/side mutation;
- incomplete checkpoint called COMPLETE;
- non-reproducible run manifest;
- large generated artifact committed to Git.

---

## 16. Branch, PR, commit and merge discipline

After IROF-G0 PASS:

- one bounded branch per packet;
- branch from latest lawful main after approved prerequisite merge;
- no stacked permanent child after parent is mergeable;
- exact head pinned in QA/gate packet;
- all generated market/large telemetry remains external;
- no force-push/history rewrite;
- eligible non-reserved packet gates auto-ratify, push and squash-merge;
- immediately continue to the next authorised packet.

Every PR body records plan/packet, authority delta, files, tests, QA, deferred work, rollback and next gate.

---

## 17. Failure handling

Correctable defects inside packet scope are repaired and retested.

Uncorrectable conditions produce BLOCKED or QUARANTINED state without weakening tests. Examples:

- source-stage contract moved incompatibly;
- required artifact unavailable;
- cross-programme authority ambiguous;
- exact scientific equivalence cannot be demonstrated;
- capacity infrastructure would require scientific scope change;
- storage root unavailable for required large artifacts.

Smallest lawful resolution is named; programme work is preserved.

---

## 18. Definition of implementation done

IROF v0.1 is complete only after all of the user's A-K terminal acceptance conditions are evidenced through the canonical interface:

A. MICRO synthetic PASS.  
B. Larger synthetic PASS.  
C. Repeated identical run equivalence PASS.  
D. Checkpoint/resume equivalence PASS.  
E. Cache reuse equivalence PASS with reduced recomputation.  
F. Clean CAPACITY_EXCEEDED without scientific mutation.  
G. Real/Validation/reserved authority failure before protected consumption.  
H. Current descriptive chain reaches furthest lawful evidence surface.  
I. Stage and whole-run telemetry recorded.  
J. Extension fixture registers without scheduler redesign.  
K. Research Operations evidence/QA/failures/negative results reproducibly addressable.

---

# Appendix A — Packet/gate matrix

| Packet | Gate | Gate type | Core result |
|---|---|---|---|
| G0 packet | IROF-G0 | OPERATOR | design + plan authority |
| WP0 | IROF-G1 | AUTO | court record/conformance freeze |
| WP1 | IROF-G2 | AUTO | core objects/schemas/registries |
| WP2 | IROF-G3 | AUTO | DAG/stage adapter planner |
| WP3 | IROF-G4 | AUTO | authority/population preflight |
| WP4 | IROF-G5 | AUTO | semantic cache |
| WP5 | IROF-G6 | AUTO | checkpoint/restart |
| WP6 | IROF-G7 | AUTO | capacity/telemetry |
| WP7 | IROF-G8 | AUTO | Research Operations integration |
| WP8 | IROF-G9 | AUTO | current adapters/profiles |
| WP9 | IROF-G10 | AUTO | synthetic full-chain |
| WP10 | IROF-G11 | AUTO | multi-N characterization |
| WP11 | IROF-G12 | AUTO closeout only | preflight/extension/terminal state |

Any real/scientific/activation authority encountered routes to its owning operator gate and is not converted into an IROF gate.

# Appendix B — Exact IROF-G0 implementation authority requested

**Request PASS for:**

- programme bootstrap/state;
- contracts/schemas/registries;
- deterministic serialization/identity;
- DAG planning/scheduling;
- read-only authority resolution;
- synthetic PopulationSpecs/generators/fixtures;
- stage adapter wrappers that preserve source semantics;
- semantic cache/reuse;
- checkpoint/restart;
- capacity/resource scheduler;
- computational telemetry;
- Research Operations/QA/catalogue/read-model integration;
- local synthetic full-chain execution;
- multi-N synthetic performance characterization;
- real-population dry-run/preflight without protected consumption;
- extension fixture;
- packet/gate evidence, PRs and eligible squash merges.

**Explicitly not requested:**

provider intake; real June C2E replay; consumption of the current SRFD June token; active selector change; C2E activation; scientific method/representation/family promotion; Validation; R2/canonical publication; C2P/C2.5/C3 semantic authority; probability/risk/exposure/trading/execution; agent write authority.

# Appendix C — Rollback strategy

IROF is additive. The primary rollback is to unregister profiles/adapters and remove the IROF CLI/read-model projection while retaining immutable evidence and source-stage artifacts. Generic refactors of SRFD primitives are permitted only after compatibility wrappers/tests prove old public behavior; if equivalence fails, retain the original SRFD implementation and keep IROF on adapters.

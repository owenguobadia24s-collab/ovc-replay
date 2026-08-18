# OVC DSAI3V CERS — Conformance Implementation Plan v0.1 REVISED 1 RATIFIED

**Plan ID:** `OVC-DSAI3V-CERS-CONFORMANCE-IMPLEMENTATION-PLAN-0.1-R1-RATIFIED`  
**Programme ID:** `OVC-DSAI3V-CERS-CONFORMANCE-v0.1`  
**Governing design:** `OVC-DSAI3V-CERS-DESIGN-SPEC-0.1-R1-RATIFIED`  
**Design pressure-test:** `OVC-DSAI3V-CERS-PRESSURE-TEST-0.1` — PASS WITH REQUIRED AMENDMENTS  
**Plan review:** `OVC-DSAI3V-CERS-PLAN-REVIEW-0.1` — PASS WITH REQUIRED AMENDMENTS  
**Repository baseline:** `main@9351a0d900064f948f78859e26d12443c04dad6c` / tree `45ed60f1a7667d52741d78e51c780fa8d6803eb2`  
**Operator ratified:** 18 August 2026  
**Status:** RATIFIED — WP0–WP5 INACTIVE/SHADOW CONFORMANCE IMPLEMENTATION AUTHORISED; LIVE UNATTENDED DISPATCH RESERVED  
**Authority effect:** bounded contracts/schemas/registries/reconciliation/fencing/shadow-adapter/tests/QA/DEVOBS only. No live unattended repository-writing dispatch, new writer identity or physical-main authority from this plan alone.

## 0. Ratified implementation decision

Implement and qualify CERS through `CERS-WP5` as an inactive/shadow DSAI3V liveness substrate. The implementation SHALL prove that already-authorized runnable work can be reconstructed, selected and **observably started in a non-writing fixture/sandbox executor** without an active conversational context.

`CERS-G-LIVE-DISPATCH` remains OPERATOR_REQUIRED before CERS may wake any repository-writing executor for unattended work.

Primary invariant:

> CERS may supervise liveness of existing authority; it may never manufacture authority to obtain liveness.

## 1. Source precedence

1. repository `main` and durable operator decisions;
2. programme-owned current authority/state;
3. `DEFAULT_EXECUTION_SUBSTRATE`;
4. DSAI v0.3 continuous execution;
5. Async Assurance live design/authority/profile;
6. VIT/SIQ/GRT contracts/current state;
7. `OVC-DSAI3V-CERS-DESIGN-SPEC-0.1-R1-RATIFIED`;
8. this ratified plan.

Missing source => fail closed.

## 2. Pre-activation authority envelope

Authorized:
- documentation/contracts/schemas/registries/fixtures;
- read-only current-state/provider adapters;
- deterministic reference reconciliation;
- programme-root registry/census;
- supervisor lease/fencing logic;
- durable dispatch transaction/worker ownership state;
- quiescence controls;
- fixture-only/non-writing executor adapter;
- shadow build-ahead simulation;
- tests/adversarial crash/race qualification;
- QA/DEVOBS/gate packets.

Denied:
- unattended repository-writing dispatch;
- branch/ref writes by a new supervisor/executor identity;
- direct or parallel physical main merge;
- independent merge token;
- force-push/history rewrite;
- programme/packet authority expansion;
- irreversible speculative side effects;
- scientific/model/selector/family/candidate/theory/semantic promotion;
- ACTIVE_DISCOVERY/ACTIVE_DEVELOPMENT/ACTIVE_VALIDATION grants;
- publication/probability/risk/exposure/trading/execution/agent-write authority.

## 3. Work packets and gates

### CERS-WP0 — source, programme-root and authority freeze

Materialise an exact current census of:
- active default substrate/controller/gateway;
- Async Assurance authority/profile;
- VIT/SIQ/GRT currentness surfaces;
- DSAI persistent runtime;
- ORCH automatic selection surface;
- registered programme-state/current-pointer roots eligible for CERS discovery;
- exact live-dispatch denial.

Required proof:
- no branch/PR/workflow/chat heuristic discovery;
- unknown/unregistered programme root => non-dispatchable;
- physical-main controller/gateway unchanged;
- operator-reserved boundaries enumerated.

**Gate `CERS-G0`: AUTO_RATIFIABLE**, authority delta `NONE`.

### CERS-WP1 — contracts, schemas and registries

Implement machine-readable:
- `ReconciliationSnapshot`
- `RunnableWorkItem`
- `RunnableWorkSet`
- `ExecutorCapabilityRecord`
- `SupervisorLease`
- `DispatchIdentity`
- `DispatchTransaction`
- `WorkerOwnership`
- `QuiescenceControl`
- `SupervisorCheckpoint`
- action/side-effect/reason-code registries
- programme-root registry

Required conservative fallbacks:
- unknown programme root => deny;
- unknown executor => deny;
- unknown action/side-effect => `IRREVERSIBLE_OR_UNKNOWN`;
- unknown start state => `UNKNOWN_START_STATE`.

**Gate `CERS-G1`: AUTO_RATIFIABLE**, inactive contracts only.

### CERS-WP2 — deterministic reference reconciler

Implement a side-effect-free reference algorithm that consumes only exact durable repository/provider observations and emits:
- `ReconciliationSnapshot`;
- ordered `RunnableWorkSet`;
- reason-coded parked/non-runnable records;
- proposed `DispatchIdentity` values, without dispatch.

Materialise canonical reference fixtures as the oracle for all later optimized/event paths.

Acceptance:
- deterministic restart;
- same inputs => same identities/order;
- operator/quiescence boundaries dominate;
- dependency/predecessor semantics preserved;
- no authority inference.

**Gate `CERS-G2`: AUTO_RATIFIABLE**.

### CERS-WP3 — fencing, wake reconciliation and crash recovery

Implement:
- exclusive supervisor lease with monotonically advancing fencing generation;
- fencing validation on every dispatch/ownership transition;
- event ingestion + periodic reference reconciliation;
- bounded configurable provider backoff/retry;
- durable dispatch transaction recovery;
- `UNKNOWN_START_STATE` resolution;
- worker heartbeat/reclaim state machine;
- `QuiescenceControl`;
- zero-chat-dependency restart.

Fatal G3 conditions:
- stale fence accepted;
- ambiguous start blindly redispatched;
- duplicate authoritative start cannot be excluded;
- restart requires chat state;
- event and reference reconciliation diverge.

**Gate `CERS-G3`: AUTO_RATIFIABLE** only if all fatal conditions are absent.

### CERS-WP4 — fixture-only executor and build-ahead actuation proof

Implement a registered **non-writing fixture/sandbox executor adapter only**.

Its `ExecutorCapabilityRecord` MUST state:
- repository write = false;
- branch/ref write = false;
- merge = false;
- force-push = false;
- irreversible external side effects = none.

It SHALL prove:
- exact dispatch identity;
- observable `START_ACKNOWLEDGED`;
- heartbeat/worker ownership;
- one authoritative start per dispatch identity;
- running background assurance does not block lawful fixture successor dispatch;
- bounded speculative construction follows existing predecessor/build-ahead rules;
- parent failure causes selective invalidation;
- unrelated lanes continue;
- failures route to existing repair owner rather than CERS remediation invention.

**Gate `CERS-G4`: AUTO_RATIFIABLE**, shadow/non-writing only.

### CERS-WP5 — adversarial qualification, rollback rehearsal and DEVOBS

Execute the complete ratified design catalogue and additionally prove:
- registered-programme census completeness for the test subject;
- reference reconciliation == optimized event path;
- `DISABLE_NEW_DISPATCH` immediately prevents new dispatch;
- `DRAIN` closes allowed owned fixture work without releasing disallowed successors;
- restart to foreground-only behavior preserves state/evidence;
- liveness: while a required background assurance future remains RUNNING and the simulated foreground caller is absent, at least one lawful successor reaches observed `START_ACKNOWLEDGED` where capacity/dependencies allow;
- unexplained runnable idle produces a liveness warning/incident.

Zero-tolerance:
- false authority allow;
- operator-boundary bypass;
- stale-fence acceptance;
- duplicate authoritative start;
- stale-worker authoritative completion;
- direct-main reachability;
- parallel physical merge;
- force-push/history rewrite;
- accepted tree mismatch;
- non-reproducible evidence.

Emit consolidated `CERS-G-LIVE-DISPATCH` gate packet.

**Gate `CERS-G5`: AUTO_RATIFIABLE** only if safety and liveness qualification PASS.

### Grouping authority

`CERS-WP1`–`CERS-WP5` MAY be grouped in one bounded inactive/shadow implementation branch/PR if:
- every logical packet/gate remains separately evidenced;
- no real repository-writing executor adapter is introduced;
- no live dispatch activation occurs;
- the grouped change remains within this exact authority envelope.

### CERS-G-LIVE-DISPATCH — unattended execution activation

**OPERATOR_REQUIRED.**

The consolidated gate packet MUST classify the exact executor as one of:

`EXISTING_QUALIFIED_EXECUTOR_IDENTITY`
or
`NEW_EXECUTOR_IDENTITY_REQUIRES_AGENT_WRITE_AUTHORITY`.

It MUST state:
- executor identity and authority sources;
- supported action classes;
- repository/branch write domains;
- merge/force-push capability;
- side-effect classes;
- fencing/start-ack/heartbeat semantics;
- registered programme allowlist/scope;
- packet/gate classes;
- worker concurrency;
- build-ahead bounds;
- all G0–G5 qualification evidence;
- unresolved warnings/incidents;
- rollback/quiescence procedure;
- explicit preservation of VIT/SIQ physical integration and all programme-owned reserved boundaries.

No generic “supervisor active” approval is valid.

### CERS-WP6 — bounded live pilot

Only after `CERS-G-LIVE-DISPATCH=PASS`.

Pilot bounds MUST be frozen before execution:
- exact programme/packet allowlist;
- exact executor identity;
- exact reversible action classes;
- maximum workers/speculative depth from existing policy;
- no new provider/science/authority domains.

Immediate pilot stop/quarantine conditions:
- duplicate authoritative start;
- stale-fence acceptance;
- unexplained runnable idle beyond the frozen liveness policy;
- direct-main reachability;
- operator-boundary false allow;
- non-reproducible completion evidence;
- S3/S4 integration incident.

### CERS-G6 — post-activation effectiveness

AUTO-ratifiable only if the bounded live pilot proves:
- real unattended successor start while background assurance runs;
- deterministic restart/reconciliation;
- no duplicate starts;
- no authority false allows;
- all physical integration still serialized through VIT/SIQ;
- rollback path remains executable;
- complete DEVOBS evidence.

## 4. Qualification catalogue

All 32 design fixtures are mandatory, plus:
- schema validation;
- identity determinism;
- programme-root/current-pointer integrity;
- capability negative reachability;
- action/side-effect conservative fallback;
- fairness/backpressure determinism;
- bounded provider backoff;
- liveness warning behavior;
- rollback rehearsal.

## 5. CI, QA and integration

- one bounded branch per packet/group;
- latest lawful main before modification;
- VIT lineage required for permanent PR;
- required repository tests, pytest/unittest parity, runner parity, FINAL_HEAD, GRT, SIQ READY and merge-readiness where applicable;
- fix correctable defects in scope and rerun;
- non-reserved PASS gates auto-ratify/merge;
- never force-push/rewrite history;
- no next permanent packet from a completed branch after lawful main integration.

## 6. DEVOBS

CERS adds the design metrics only when observed. Missing values remain `UNAVAILABLE`.

G5 effectiveness summary MUST separate:
- time runnable but not executing for genuine reasons;
- time runnable and idle without a genuine reason;
- background assurance elapsed;
- useful development overlap;
- physical serialized integration wait.

## 7. Rollback

Pre-activation: forward-disable/supersede CERS shadow surfaces.

Post-activation: durable `DISABLE_NEW_DISPATCH`, drain/cancel owned work under packet contracts, return new work to explicit foreground invocation, preserve all CERS/DSAI/VIT/DEVOBS history.

## 8. Plan-review amendments incorporated

All `PR-CERS-01`…`PR-CERS-08` amendments are incorporated:
- WP4 non-writing capability proof;
- WP0 registered-root census;
- WP2 reference oracle;
- WP3 fencing/unknown-start fatality;
- G5 liveness criterion;
- exact executor classification at activation;
- rollback rehearsal;
- bounded live-pilot stop conditions.

## 9. Ratified terminal pre-activation target

`CERS_IMPLEMENTED_QUALIFIED_INACTIVE_OR_SHADOW / CERS-G-LIVE-DISPATCH GATE_READY`

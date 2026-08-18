# OVC DSAI3V Continuous Execution Reconciler / Supervisor — Design Specification v0.1 REVISED 1 RATIFIED

**Document ID:** `OVC-DSAI3V-CERS-DESIGN-SPEC-0.1-R1-RATIFIED`  
**Programme:** `OVC-DSAI3V-CERS-CONFORMANCE-v0.1`  
**Architecture lineage:** `OVC-DSAI-v0.3` / `OVC-DSAI-VIT-v0.3` / `OVC-DSAI3V-ASYNC-ASSURANCE-CONFORMANCE-v0.1`  
**Repository baseline used for design:** `main@9351a0d900064f948f78859e26d12443c04dad6c` / tree `45ed60f1a7667d52741d78e51c780fa8d6803eb2`  
**Pressure-test:** `OVC-DSAI3V-CERS-PRESSURE-TEST-0.1` — PASS WITH REQUIRED AMENDMENTS  
**Ratified:** 18 August 2026  
**Status:** RATIFIED ADDITIVE DSAI3V DESIGN  
**Authority effect:** DESIGN CANON ONLY. Runtime implementation and live unattended dispatch remain separately governed.

## Ratified primary decision

DSAI3V SHALL gain a Continuous Execution Reconciler / Supervisor (CERS) that continuously reconstructs runnable work from durable repository state and, when separately activated, wakes the existing authorized execution substrate without requiring an active conversational invocation.

CERS SHALL NOT infer authority, become a second merge controller, bypass programme gates, or directly mutate physical `main`.

> **Ratified rule:** Runnable already-authorized work must be recoverable without chat state; background assurance may delay materialisation but must not create avoidable construction idleness.

## 1. Constitutional rules

**CERS-D1 — Repository state is the continuation source of truth.** Chat history is never required for recovery or work discovery.

**CERS-D2 — Reconciliation is zero-authority.** Runnable classification cannot grant programme, packet, writer, merge or scientific authority.

**CERS-D3 — Explicit registered discovery only.** CERS enumerates only registered programme-state/current-pointer roots and exact packet records. Branch/PR/workflow naming and chat text are never authority/discovery sources.

**CERS-D4 — Existing owner authority is mandatory.** Exact current programme authority, authority delta and packet scope must permit the action.

**CERS-D5 — Operator boundaries dominate.** `HOLD`, operator-required gates, reserved authority and durable quiescence controls park new dispatch.

**CERS-D6 — Physical main remains VIT/SIQ-only.** CERS never directly writes/merges `main`; `DSAI_VIT_PHYSICAL_CONTROLLER` and `DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY` remain controlling.

**CERS-D7 — Parallel build does not permit parallel physical merge.** `parallel_physical_merge=false` remains invariant.

**CERS-D8 — Live unattended writer activation is separately governed.** Any capability that wakes repository-writing work after the conversational invocation ends requires `CERS-G-LIVE-DISPATCH` operator PASS with exact executor identity/capabilities.

**CERS-D9 — Running eligible assurance is not a construction stop.** Async Assurance semantics remain controlling.

**CERS-D10 — Unknown/missing state fails closed.** Unknown executor, action class, authority, programme root, dependency, worker ownership or start state is non-dispatchable until reconciled.

## 2. Normative state

### `ReconciliationSnapshot`
Content-addressed exact observation of:
- main commit/tree;
- active default substrate;
- registered programme state/current pointers;
- mandate/lane state;
- packet/PIP/VIT/dependency identities;
- Async Assurance futures/sets;
- VIT/SIQ train/currentness;
- open dispatch transactions;
- executor capability and worker ownership;
- quiescence/operator boundaries.

### `RunnableWorkItem` / `RunnableWorkSet`
Exact deterministic dispatch candidates. Each item binds programme/packet/generation, authority manifest, predecessor requirement, dependency frontier, action class, side-effect class, speculation class and reason code.

### `ExecutorCapabilityRecord`
Versioned declaration for one dispatch target:
- executor identity;
- supported action classes;
- repository write capability;
- branch/ref write domains;
- merge capability;
- force-push capability;
- irreversible-side-effect capabilities;
- start acknowledgement mechanism;
- heartbeat mechanism;
- fencing-token support;
- authority source.

Unknown/unregistered executor capability => deny.

### `SupervisorLease`
Exclusive supervisor ownership with monotonically advancing `fencing_generation`. Every dispatch and worker-ownership transition must validate the current generation. Lease expiry without fencing is insufficient.

### `DispatchIdentity`
Content-addressed identity of exact packet generation + requested action + executor + authority + dependency/currentness frontier. Retry reuses the same logical identity when inputs are unchanged.

### `DispatchTransaction`
Durable phases:
`PREPARED`, `DISPATCH_REQUESTED`, `START_ACKNOWLEDGED`, `RUNNING`, `OUTCOME_OBSERVED`, `COMPLETED`, `FAIL_CORRECTABLE`, `FAIL_BLOCKING`, `CANCELLED`, `SUPERSEDED`, `UNKNOWN_START_STATE`.

A crash after `DISPATCH_REQUESTED` but before `START_ACKNOWLEDGED` enters reconciliation; blind redispatch is prohibited until the exact start state is resolved or the provider contract proves idempotent reuse.

### `WorkerOwnership`
Exact packet-generation ownership with executor identity, fencing generation, heartbeat and reclaim state. A stale worker cannot authoritatively complete a superseded transaction.

### `QuiescenceControl`
Durable operator/control-plane state:
- `RUN`
- `DRAIN`
- `HOLD`
- `DISABLE_NEW_DISPATCH`

`HOLD`/`DISABLE_NEW_DISPATCH` prevent new work; `DRAIN` allows already-owned reversible work to close safely but starts no successors unless explicitly allowed by the governing packet contract.

### `SupervisorCheckpoint`
Fresh-process recovery state; `chat_dependency_count=0`.

## 3. Deterministic reconciliation algorithm

Each pass SHALL:

1. resolve exact current `main`;
2. read `DEFAULT_EXECUTION_SUBSTRATE`;
3. enumerate only registered programme roots;
4. validate current programme pointers/states;
5. reconstruct persistent mandates and lanes;
6. reconcile Async Assurance futures/sets using exact provider observations;
7. reconcile VIT/SIQ/currentness and predecessor requirements;
8. reconcile supervisor lease, dispatch transactions and worker ownership;
9. apply quiescence/operator boundaries;
10. validate executor capability and side-effect class;
11. compute deterministic `RunnableWorkSet`;
12. apply existing build-ahead/capacity/fairness budgets;
13. persist checkpoint/intent before dispatch;
14. after any observed transition, reconcile again.

Unchanged inputs => identical logical decision.

## 4. Action and side-effect classification

Every dispatchable action SHALL declare:
- `action_class`;
- `side_effect_class`;
- exact write domains where any;
- whether speculative execution is permitted.

Minimum side-effect classes:
- `READ_ONLY`
- `LOCAL_REVERSIBLE`
- `BRANCH_REVERSIBLE`
- `EXTERNAL_REVERSIBLE`
- `IRREVERSIBLE`
- `IRREVERSIBLE_OR_UNKNOWN`

Unknown/missing => `IRREVERSIBLE_OR_UNKNOWN`.

Speculative successors may use only action classes already authorized by their programme and side-effect classes specifically allowed by the existing speculative-successor contract. `IRREVERSIBLE` and `IRREVERSIBLE_OR_UNKNOWN` are barred before authoritative predecessor satisfaction.

## 5. Wake, sweep and liveness

Wake sources may include provider completion, main movement, programme-state update, worker outcome, lease expiry and operator decision.

Events are optimizations. A durable reference reconciliation sweep is mandatory for missed-event recovery.

The operational cadence/backoff SHALL be configurable and bounded. Provider outage/rate limit must not cause tight polling or silent permanent idleness.

A runnable lane with available declared capacity and no genuine stop condition accumulates `runnable_idle_ms`. Crossing a versioned liveness threshold emits a warning/incident; the threshold is an operational policy value to be measured and frozen, not invented by this design.

## 6. Execution start must be observed

CERS may claim dispatch liveness only if `START_ACKNOWLEDGED` is observed through the registered executor contract. A persisted intent or successful API call alone is not proof of useful development work.

Worker heartbeat confirms ongoing ownership. Missing heartbeat follows the executor's reclaim contract and never authorizes duplicate concurrent ownership.

## 7. Build-ahead and invalidation

Async Assurance and existing DSAI/VIT predecessor semantics remain controlling.

- `PHYSICAL_MATERIALISATION_REQUIRED` blocks successor build-ahead.
- `QUALIFIED_VIT_GENERATION_REQUIRED`, `PAYLOAD_OUTPUT_REQUIRED`, `EXECUTION_COMPLETION_REQUIRED`, `ORDER_ONLY` and `NONE` are interpreted only through their existing registered contracts.
- exact predecessor landing may promote compatible speculative work without rebuild;
- parent failure or payload/dependency change invalidates only the affected descendant frontier;
- unrelated lanes remain runnable.

CERS does not invent remediation. Correctable failures route to the governing programme/DSAI repair owner.

## 8. Split-brain and duplicate prevention

Zero-tolerance invariants:
- at most one current supervisor fencing generation per ownership domain;
- stale fencing generation rejected;
- at most one authoritative worker ownership per packet generation;
- duplicate wake does not create duplicate start;
- duplicate/retried dispatch reuses one `DispatchIdentity`;
- stale worker outcome cannot complete a superseded packet generation;
- CERS never creates a second physical merge lease.

## 9. Recovery and restart

Fresh-process reconciliation must recover:
- open supervisor lease state;
- all dispatch transactions;
- ambiguous start state;
- worker ownership/heartbeats;
- pending assurance futures;
- current programme pointers;
- VIT/SIQ frontiers;
- quiescence state.

Reference reconciliation and event-optimized paths MUST converge to identical logical snapshot, runnable set and transaction outcomes.

## 10. DEVOBS

Observed metrics:
`reconciliation_count`, `reconciliation_elapsed_ms`, `runnable_work_count`, `runnable_idle_ms`, `wake_to_reconcile_ms`, `reconcile_to_dispatch_ms`, `dispatch_to_start_ack_ms`, `worker_running_ms`, `duplicate_wake_count`, `dispatch_reuse_count`, `dispatch_supersession_count`, `lease_reclaim_count`, `split_brain_reject_count`, `missed_event_recovery_count`, `speculative_successor_count`, `speculative_work_salvaged_ms`, `speculative_work_discarded_ms`.

Unknown remains `UNAVAILABLE`.

Primary effectiveness KPI:
> fraction of runnable already-authorized construction wall time overlapped with observed worker execution, excluding genuine operator/authority/dependency/materialisation stops.

## 11. Mandatory qualification catalogue

Before live unattended dispatch activation, prove at least:

1. conversational process disappears while AA0 runs; lawful successor dispatches in shadow;
2. duplicate wake storm is idempotent;
3. missed wake is recovered by sweep;
4. out-of-order provider observations converge;
5. two supervisors contend; one fencing generation wins;
6. stale supervisor dispatch is rejected;
7. crash after intent persist before dispatch;
8. crash after dispatch request before start acknowledgement => `UNKNOWN_START_STATE`;
9. provider proves idempotent start lookup/recovery;
10. worker crash/heartbeat loss with safe reclaim;
11. stale worker completion after supersession rejected;
12. content-addressed duplicate dispatch yields one authoritative start;
13. unregistered programme root cannot be dispatched;
14. unregistered executor cannot be dispatched;
15. unknown side-effect class cannot speculative-dispatch;
16. parent correctable failure selectively invalidates descendants;
17. blocking lane leaves unrelated lane runnable;
18. operator-required boundary parks;
19. durable HOLD dominates wake;
20. `PHYSICAL_MATERIALISATION_REQUIRED` blocks build-ahead;
21. eligible predecessor requirement permits bounded speculative construction;
22. main movement preserves valid AA0 and selectively renews;
23. provider outage/rate limit uses bounded recovery/backoff;
24. current pointer missing/conflicting fails closed;
25. reference reconciliation == event-optimized path;
26. supervisor restart with zero chat context chooses same next action;
27. VIT/SIQ remains sole physical integration route;
28. no direct CERS main write/merge;
29. no force-push/history rewrite;
30. liveness warning occurs for unexplained runnable idle;
31. build-ahead budget prevents unbounded speculative work;
32. failure outcome routes to existing repair owner, not CERS-invented remediation.

## 12. Implementation / activation boundary

Ratification of this design authorizes creation of a repository-specific conformance implementation plan.

Implementation may include contracts, schemas, registered programme discovery, deterministic reconciler, supervisor lease/fencing logic, durable dispatch transactions, capability declarations, shadow/non-writing dispatch adapter, tests, adversarial fixtures, QA and DEVOBS.

**Live unattended dispatch remains denied until `CERS-G-LIVE-DISPATCH` operator PASS.**

The activation packet must name:
- exact executor identity;
- repository/branch write capability;
- merge/force-push capability;
- action and side-effect classes;
- fencing validation;
- start/heartbeat semantics;
- registered programme scope;
- packet/gate classes;
- rollback;
- all qualification evidence.

No new scientific/Validation/publication/probability/risk/exposure/trading/execution authority may be bundled into that gate.

## 13. Rollback

Before activation: forward-disable/supersede CERS shadow routing.

After activation: set quiescence to `DISABLE_NEW_DISPATCH`, drain/cancel already-owned work according to packet contracts, return new work to explicit foreground invocation, preserve all leases/intents/outcomes/checkpoints/DEVOBS and Git history.

## 14. Pressure-test amendments incorporated

All required amendments from `OVC-DSAI3V-CERS-PRESSURE-TEST-0.1` are incorporated:
- executor capability/start/heartbeat semantics;
- fencing generations;
- registered programme roots;
- content-addressed dispatch identity;
- bounded recovery/backoff and starvation observability;
- explicit unattended activation boundary;
- machine-readable side-effect classification;
- reference reconciliation convergence;
- dispatch transaction/unknown-start recovery;
- repair-owner separation;
- durable quiescence control.

## 15. Ratified terminal state

`CERS_DESIGN_RATIFIED_IMPLEMENTATION_PLAN_REQUIRED`

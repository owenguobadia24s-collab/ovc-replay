# OVC DSAI3V Continuous Execution Reconciler / Supervisor — Design Specification v0.1 PROPOSED

**Document ID:** `OVC-DSAI3V-CERS-DESIGN-SPEC-0.1`  
**Programme:** `OVC-DSAI3V-CERS-CONFORMANCE-v0.1`  
**Architecture lineage:** `OVC-DSAI-v0.3` / `OVC-DSAI-VIT-v0.3` / `OVC-DSAI3V-ASYNC-ASSURANCE-CONFORMANCE-v0.1`  
**Repository baseline:** `main@9351a0d900064f948f78859e26d12443c04dad6c` / tree `45ed60f1a7667d52741d78e51c780fa8d6803eb2`  
**Prepared:** 18 August 2026  
**Status:** PROPOSED FOR ADVERSARIAL PRESSURE-TEST  
**Authority effect:** DESIGN ONLY. No unattended dispatch, new writer identity, physical merge capability, programme authority, scientific authority, Validation, publication, probability, risk, exposure or execution authority is created.

## 0. Problem statement

The current repository has the major components of continuous execution but not a host-independent liveness guarantee.

DSAI v0.3 defines persistent continuation mandates, ordered landing, automatic successor release and zero-chat-dependency recovery. `vit_runtime.py` can drain durable state and return a next lawful action such as `START_SUCCESSOR`, `WAITING_PREREQUISITE`, `WAITING_OPERATOR_AUTHORITY`, `STOP` or `HOLD`. Async Assurance makes ordinary GitHub assurance background-reusable and permits lawful successor build-ahead while materialisation waits. ORCH-3/4/5 can select packet trains and parallel-safe construction. VIT/SIQ owns physical-main serialization.

The remaining gap is actuation and liveness:

> A durable decision that a successor is runnable does not by itself prove that a worker was actually awakened, owned the lane, started execution, persisted the outcome and reconciled again after the conversational invocation ended.

CERS is the proposed missing liveness layer.

## 1. Primary objective

CERS SHALL make continuous packet execution recoverable and continuously actuated independently of any single chat turn, while preserving all existing authority and physical-integration boundaries.

Target loop:

`observe durable state -> reconcile -> compute runnable work -> acquire fenced supervisor ownership -> dispatch existing execution substrate -> persist start/outcome -> reconcile again`

CERS SHALL NOT become a second merge controller and SHALL NOT infer or create authority.

## 2. Architectural placement

CERS sits above the existing execution primitives:

- **Programme state / current pointers**: court-record packet and authority state.
- **DSAI3V persistent mandate runtime**: command semantics and next-action resolution.
- **Async Assurance**: durable `AssuranceFuture`, exact `RequiredAssuranceSet`, wake/reconciliation semantics.
- **ORCH-3/4/5**: packet-train and parallel-build selection.
- **VIT**: prospective integration lineage, dependency frontiers, invalidation and current-state resolution.
- **SIQ**: only serialized physical-main integration gateway.
- **GRT**: repository conformance/currentness.
- **DEVOBS**: observed execution/liveness evidence.

CERS owns only **liveness coordination, reconciliation and dispatch intent lifecycle**.

## 3. Constitutional rules

**CERS-D1 — Repository state is the continuation source of truth.** Chat transcript or assistant memory may never be required to determine runnable work.

**CERS-D2 — Reconciliation is authority-neutral.** Observing that work is runnable does not grant permission to execute it.

**CERS-D3 — Existing owner authority is mandatory.** A packet is dispatchable only if its governing programme already authorizes the exact action and authority delta.

**CERS-D4 — Operator-reserved boundaries park.** CERS may prepare evidence but must not cross any operator-required gate or reserved authority delta.

**CERS-D5 — Physical main remains exclusively serialized.** CERS may never directly mutate `main`; VIT/SIQ remains the only physical integration path.

**CERS-D6 — No parallel physical merge.** Build concurrency does not imply integration concurrency.

**CERS-D7 — No new writer identity by implication.** A new autonomous repository-writing worker/service identity is an explicit authority surface and cannot be inferred from this design.

**CERS-D8 — Running ordinary assurance is not a development stop.** AA0/eligible background assurance may remain running while lawful build-ahead continues.

**CERS-D9 — Irreversible speculative side effects remain barred.** Build-ahead may perform only already-authorized reversible/local/branch/VIT work until predecessor authority conditions are satisfied.

**CERS-D10 — Fail closed on ambiguity.** Missing programme state, owner authority, dependency frontier, worker capability, lease state, exact packet generation or required evidence makes the action non-dispatchable.

## 4. Normative objects

### `ReconciliationSnapshot`
Content-addressed, read-only observation of the exact repository/control state used for one CERS decision. It SHALL bind at minimum:
- physical main commit/tree;
- programme state/current pointer identities;
- active mandate/lane state;
- exact packet generations and predecessor requirements;
- required-assurance future/set states;
- VIT train/currentness state;
- open dispatch/worker ownership;
- operator-boundary state;
- observed provider state references where needed.

### `RunnableWorkItem`
One exact potentially-dispatchable packet generation with:
- programme/packet/payload/PIP/VIT identities;
- authority manifest;
- predecessor requirement;
- dependency frontier;
- current build status;
- speculation class;
- required reversible action class;
- reason code.

### `RunnableWorkSet`
Deterministically ordered set of `RunnableWorkItem` values selected from one exact `ReconciliationSnapshot`.

### `SupervisorLease`
Exclusive logical ownership of one reconciliation/dispatch domain. It SHALL include a monotonically advancing fencing generation. Expiry alone does not permit an old holder to continue acting.

### `DispatchIntent`
Durable idempotent request to the existing execution substrate for one exact packet generation. It SHALL bind:
- `RunnableWorkItem`;
- supervisor lease/fencing generation;
- executor adapter identity;
- authority manifest;
- requested action;
- idempotency key;
- creation reason.

States: `PREPARED`, `DISPATCHABLE`, `DISPATCHED`, `START_ACKNOWLEDGED`, `RUNNING`, `COMPLETED`, `FAIL_CORRECTABLE`, `FAIL_BLOCKING`, `CANCELLED`, `SUPERSEDED`, `NOT_EVALUABLE`.

### `DispatchOutcome`
Durable terminal or progress evidence bound to the exact `DispatchIntent`, executor identity and packet generation.

### `WorkerOwnership`
Proof that one authorized execution worker owns one exact packet generation. It SHALL support heartbeat/expiry/reclaim and stale-owner fencing.

### `SupervisorCheckpoint`
Durable minimal state required for fresh-process recovery with zero chat dependency.

## 5. Deterministic reconciliation

CERS SHALL derive runnable work only from explicit repository-native records and registered adapters. It SHALL NOT guess work from branch names, PR titles, workflow names or chat text.

A reconciliation pass SHALL:

1. load current physical main and active default substrate;
2. resolve current programme state and current pointers;
3. reconstruct durable mandates/lanes;
4. reconcile Async Assurance futures and required sets;
5. reconcile VIT/currentness/train state;
6. reconcile existing dispatch/worker ownership;
7. apply operator-boundary and authority checks;
8. compute exact `RunnableWorkSet`;
9. choose only actions permitted by capacity/build-ahead/fairness policy;
10. persist intents/checkpoint before side-effecting dispatch.

Repeated reconciliation against unchanged inputs MUST be idempotent.

## 6. Wake and recovery model

CERS SHOULD be event-driven but MUST NOT rely on events as the sole liveness source.

Wake sources may include:
- GitHub assurance terminal observations;
- physical main advancement;
- programme-state/current-pointer update;
- worker completion/failure;
- lease expiry;
- explicit operator decision;
- manual recovery dispatch.

A periodic reconciliation sweep SHALL exist as missed-event recovery. Exact cadence is an operational parameter to be measured and frozen separately; this design does not invent one.

Duplicate, delayed, missed and out-of-order wakes are normal inputs and must converge to the same logical state.

## 7. Build-ahead semantics

CERS SHALL maximize lawful construction utilization without weakening dependency semantics.

If packet A is `WAITING_ASSURANCE` but successor B has a predecessor requirement that permits speculative construction, B may be dispatched as `SPECULATIVE_RUNNING` within the existing build-ahead budget.

If A later materialises exactly as predicted and B's dependency frontier remains valid, B may promote without rebuild.

If A fails or changes:
- only descendants whose declared dependency frontier is affected are invalidated;
- unaffected work is preserved;
- irreversible side effects already barred remain barred.

If B requires `PHYSICAL_MATERIALISATION_REQUIRED`, CERS must not dispatch B before A physically lands.

## 8. Dispatch and executor boundary

The CERS core SHALL be provider-neutral and SHALL not itself implement packet work.

An `ExecutorAdapter` translates an exact `DispatchIntent` into a wake/dispatch request for an already-authorized execution substrate.

The first implementation target is the existing DSAI3V execution substrate. The design does not assume that GitHub Actions can wake a ChatGPT conversation. If live unattended execution requires a separate persistent service, Codex worker, hosted agent, runner or other repository-writing identity, that exact identity/capability is a separately governed activation delta.

No adapter may:
- broaden packet classes;
- infer owner authority;
- bypass programme gates;
- bypass VIT/SIQ;
- force-push;
- rewrite history;
- perform publication/provider intake/scientific or trading actions absent their own authority.

## 9. Split-brain and duplicate-dispatch safety

CERS SHALL treat split-brain as a zero-tolerance safety condition.

Required controls:
- one authoritative supervisor lease per ownership domain;
- monotonically advancing fencing generation;
- every dispatch binds the fencing generation;
- stale holder action is rejected even if its clock says the old lease remains valid;
- dispatch idempotency key prevents duplicate authoritative start;
- worker ownership prevents two workers from simultaneously owning the same packet generation;
- recovery may reissue the same logical dispatch only idempotently.

## 10. Failure behavior

Correctable packet failures route to the existing bounded repair/retry policy.

Supervisor/provider failures SHALL not silently mark a packet complete.

Required dispositions:
- `WAITING_EVENT_OR_RECONCILIATION`
- `WAITING_WORKER_CAPACITY`
- `WAITING_PREREQUISITE`
- `WAITING_OPERATOR_AUTHORITY`
- `RECOVERING`
- `BLOCKED`
- `QUARANTINED`
- `COMPLETED`

A lane with no blocker but runnable work must not remain indefinitely idle without emitting an observed liveness warning/incident.

Provider outage or rate limit SHALL degrade to reconciliation backoff/recovery without manufacturing PASS, completion or authority.

## 11. Backpressure and fairness

CERS SHALL respect the existing DSAI/ORCH build-ahead and portfolio caps. It may not create unbounded speculative branch trains.

The implementation SHALL define:
- maximum concurrent dispatches from existing policy;
- maximum speculative depth from existing `BuildAheadBudget`;
- deterministic queue/fairness order;
- starvation detection;
- per-lane isolation so a blocked lane does not stop unrelated runnable lanes.

## 12. DEVOBS and liveness evidence

Observed CERS metrics SHOULD include:
- `reconciliation_count`
- `reconciliation_elapsed_ms`
- `runnable_work_count`
- `runnable_idle_ms`
- `wake_to_reconcile_ms`
- `reconcile_to_dispatch_ms`
- `dispatch_to_start_ack_ms`
- `worker_running_ms`
- `duplicate_wake_count`
- `dispatch_reuse_count`
- `dispatch_supersession_count`
- `lease_reclaim_count`
- `split_brain_reject_count`
- `missed_event_recovery_count`
- `speculative_successor_count`
- `speculative_work_salvaged_ms`
- `speculative_work_discarded_ms`

Unknown telemetry remains `UNAVAILABLE`, never inferred.

Primary liveness KPI:
> For runnable, already-authorized work with available declared capacity and no genuine stop condition, measure the fraction of wall time during which at least one eligible construction worker is actually executing rather than waiting on background assurance.

Safety KPIs remain zero tolerance:
- false authority allow;
- operator-boundary bypass;
- duplicate authoritative packet execution;
- duplicate effective physical merge;
- stale-fence dispatch acceptance;
- direct CERS main mutation;
- accepted exact-tree mismatch.

## 13. Qualification requirements

Before any live unattended dispatch activation, deterministic/adversarial coverage SHALL include at least:

1. chat/process disappears while AA0 remains running; successor still dispatches in shadow;
2. duplicate wake storm;
3. missed wake recovered by periodic reconciliation;
4. out-of-order provider completion;
5. two supervisors start simultaneously; one is fenced;
6. supervisor dies after intent persist before dispatch;
7. supervisor dies after dispatch before start acknowledgement;
8. worker dies mid-packet and is safely reclaimed;
9. stale worker reports completion after supersession;
10. parent correctable failure selectively invalidates descendants;
11. blocking failure in one lane leaves unrelated lane runnable;
12. operator-required gate parks exactly;
13. physical-materialisation-required predecessor blocks speculative successor;
14. payload-output-required predecessor permits only declared build-ahead;
15. main movement preserves valid AA0 work and renews only affected placement/currentness evidence;
16. provider outage/rate limit;
17. programme state pointer missing/conflicting => fail closed;
18. unregistered executor identity => deny;
19. executor adapter write/merge negative reachability where not explicitly authorized;
20. VIT/SIQ remains sole physical integration route;
21. restart from durable state yields same next action as uninterrupted execution;
22. reference reconciliation and optimized event path converge;
23. no runnable-idle interval without a reason/observable warning;
24. bounded build-ahead prevents unbounded speculative work.

## 14. Implementation and activation boundary

This design authorizes no runtime changes by itself.

A conformance implementation plan may authorize contracts, schemas, deterministic reconciler, inactive/shadow supervisor, read-only provider adapters, non-writing dispatch simulations, tests, QA and DEVOBS.

**Live unattended dispatch is OPERATOR_REQUIRED** if it can cause an execution worker to perform repository writes in the absence of an active conversational invocation. The gate must name the exact executor identity/capabilities, fencing model, dispatch scope, packet classes, write domains and rollback.

A same-controller wake that is already within an existing qualified writer identity may be proposed as a bounded activation delta, but it still requires explicit CERS live-dispatch approval because it activates a deferred unattended capability.

## 15. Rollback

Before live activation: disable/supersede CERS shadow reconciliation/dispatch simulation and preserve evidence.

After any future activation: forward-disable new unattended dispatch, let already-owned safe operations drain or cancel under their packet contract, return execution to explicit foreground invocation while preserving all intents/outcomes/leases/checkpoints/DEVOBS evidence and Git history.

No force-push/history rewrite.

## 16. Proposed terminal design state

`CERS_DESIGN_PROPOSED_PRESSURE_TEST_REQUIRED`

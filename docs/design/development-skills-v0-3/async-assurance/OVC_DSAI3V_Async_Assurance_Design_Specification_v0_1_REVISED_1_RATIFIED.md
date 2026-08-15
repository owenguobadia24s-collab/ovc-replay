# OVC DSAI3V Async Assurance — Design Specification v0.1 REVISED 1 RATIFIED

**Document ID:** `OVC-DSAI3V-ASYNC-ASSURANCE-DESIGN-SPEC-0.1-R1-RATIFIED`  
**Programme lineage:** `OVC-DSAI-v0.3` / `OVC-DSAI-VIT-v0.3`  
**Prepared / ratified:** 15 August 2026  
**Repository baseline used for design:** `main@4492bc55f9da25f3d8b2f9b1ade4a7d77b88bfeb`  
**Evaluation:** `OVC-DSAI3V-ASYNC-ASSURANCE-EVALUATION-0.1` — PASS WITH REQUIRED AMENDMENTS  
**Status:** RATIFIED ADDITIVE DESIGN AMENDMENT  
**Authority effect:** DESIGN CANON ONLY. Runtime implementation/activation remains separate.

## Ratified primary decision

DSAI3V SHALL execute required GitHub Actions assurance asynchronously with respect to development construction. Required assurance continues to gate physical materialisation, but running workflows SHALL NOT by themselves pause an otherwise-lawful continuous-development mandate. Lawful successor construction may continue under the existing dependency frontier, `PacketPredecessorRequirement`, `BuildAheadBudget` and speculative-successor rules.

Workflow completion is a **zero-authority wake signal**. It cannot itself authorize or perform a merge. It wakes the existing DSAI/VIT physical controller, which re-evaluates the exact closed materialisation predicate and may request the already-authorized serialized squash materialisation only if every prerequisite remains true.

> **Ratified rule:** Workflow completion may gate materialisation; workflow execution must not block lawful development construction.

This amendment refines execution semantics already implied by DSAI3-D10, DSAI3-D127…D130, DSAI3-D145…D154 and DSAI3-D210…D218. DSAI3-D1…D310 remain unchanged and authoritative.

## 1. Constitutional rules

**AA-D1 — Assurance is evidence, not authority.** Workflow/check results cannot create programme, gate, merge, scope or scientific authority.

**AA-D2 — Background does not mean optional.** Required background checks remain mandatory for physical materialisation.

**AA-D3 — Development and landing remain separate resources.** Build slots may stay productive while assurance or the serialized physical frontier lags.

**AA-D4 — Existing reserved boundaries remain reserved.** Operator-required gates, authority deltas, destructive actions, force-push/history rewrite, scientific/Validation/publication/probability/risk/exposure/execution and programme-owned denials are unchanged.

**AA-D5 — Physical main remains the operational court record.** A prospective packet is not complete merely because workflows are green.

## 2. Normative objects

### `AssuranceFuture`
Durable state for one exact assurance profile executing against one exact packet/PIP/VIT binding.

Required identity/binding fields include `packet_id`, `payload_id`, `vit_generation_id` where applicable, `assurance_profile_id`, `assurance_class`, exact candidate commit and/or tree identity, required-assurance-set identity, provider adapter identity, workflow/check references, dependency/currentness frontier and supersession lineage.

States: `CREATED`, `RUNNING`, `PASS`, `FAIL_CORRECTABLE`, `FAIL_BLOCKING`, `STALE`, `CANCELLED`, `SUPERSEDED`, `NOT_EVALUABLE`.

### `AssuranceCompletionSignal`
Zero-authority durable terminal observation for an exact provider run/check and exact future binding. Duplicate, delayed and out-of-order delivery MUST be idempotent.

### `RequiredAssuranceSet`
Versioned exact membership of the assurance futures/checks required for one materialisation intent. It defines required members, admissible terminal result for each member, whether a member is reusable across placement change, and the exact dependency/currentness scope. Any membership change creates a new set identity and supersedes the old materialisation intent.

### `ConditionalMaterialisationIntent`
Durable pre-authorized request for an already-authorized packet to enter materialisation only after the complete current predicate becomes true.

It binds packet/PIP/VIT/train identities, expected predecessor/result tree, gate/authority manifest, `RequiredAssuranceSet`, GRT/currentness requirements, blocker/review rules, physical materialisation profile and `REQUEST_SERIALIZED_SQUASH_MATERIALISATION` as the only automatic side-effect action.

States: `PREPARED`, `WAITING_ASSURANCE`, `WAITING_PREDECESSOR`, `WAITING_CURRENTNESS`, `WAITING_OPERATOR`, `WAITING_LEASE`, `MATERIALISATION_READY`, `CONSUMED`, `BLOCKED`, `CANCELLED`, `SUPERSEDED`.

### `AssuranceWakeSubscription`
Provider-neutral durable mapping from assurance terminal observations to exact futures/intents and controller wakeup. The subscription itself owns no write capability.

## 3. Assurance stratification

**AA-D6 — Four operational bands.**

- `AA0_BACKGROUND_REUSABLE`: packet-local/base-independent tests and deterministic checks whose declared dependencies do not include final physical placement.
- `AA1_PROSPECTIVE_TREE_BOUND`: tests/GRT/A2 evidence bound to one exact prospective VIT generation/tree.
- `AA2_MATERIALISATION_EDGE`: mutable currentness checks that must be fresh near/immediately before write, including owner authority, programme-state/current-pointer consistency, blocking review state, active train placement, exact predecessor, security, required GRT currentness and SIQ/lease readiness.
- `AA3_POST_WRITE_EQUIVALENCE`: physical tree equality, receipt binding and effective completion.

**AA-D7 — Run early what can be reused.** AA0 begins as soon as a stable packet generation exists; AA1 begins when the exact prospective tree exists; AA2 is delayed or renewed at the materialisation edge; AA3 is post-write only.

**AA-D8 — Explicit classification only.** Every assurance profile/check MUST declare `dependency_scope` and `reuse_class`. Classification is never inferred from a workflow/job name. Unknown or missing classification defaults to `AA2_MATERIALISATION_EDGE` / no reuse.

**AA-D9 — Reuse is dependency-scoped.** Reorder/main movement renews only evidence whose declared frontier changed.

**AA-D10 — Stale green is not materialisation green.** PASS on a superseded head/PIP/VIT/authority generation remains historical evidence but cannot satisfy a current intent.

## 4. Continuous successor execution

**AA-D11 — Workflow wait does not pause the mandate.** `AssuranceFuture.RUNNING` alone cannot transition a continuous mandate to operator wait or completed state.

**AA-D12 — Existing speculative-successor rules control build-ahead.** A successor may become `SPECULATIVE_RUNNING` only where the existing dependency contract and `BuildAheadBudget` allow it.

**AA-D13 — Speculative irreversible-side-effect barrier.** `SPECULATIVE_RUNNING` may perform reversible/local/branch/VIT construction and assurance already within the successor’s authority. It MUST NOT consume irreversible external side effects merely because build-ahead is permitted. Provider intake, publication, external durable programme writes, operator-reserved actions and any other irreversible programme-owned effect require authoritative predecessor satisfaction plus their own current authority.

**AA-D14 — No speculative authority promotion.** Speculative completion of code/tests cannot make a successor physically effective or cross a reserved boundary.

**AA-D15 — Exact predecessor landing promotes without rebuild.** If predecessor materialises as predicted and the dependency frontier remains valid, existing `SPECULATIVE_RUNNING -> AUTHORITATIVE_RUNNING` behavior applies without restart.

**AA-D16 — Failed parent causes selective invalidation.** Descendants are invalidated only according to the existing dependency/invalidation graph; unaffected work is preserved.

## 5. Conditional materialisation

**AA-D17 — Intent may be prepared while workflows run.** Implementation/QA preparation may persist the exact materialisation intent before required assurance completes.

**AA-D18 — Workflow completion wakes; it does not merge.** The signal adapter only updates futures and wakes the controller.

**AA-D19 — Exact complete assurance set required.** Every required member of the exact `RequiredAssuranceSet` must reach its allowed terminal PASS state. Queued, running, skipped-required, cancelled-required, stale, superseded or unavailable members do not satisfy readiness.

**AA-D20 — Existing closed readiness predicate remains controlling.** The controller may transition to `MATERIALISATION_READY` only when all DSAI3-D127 conditions are true for the exact current generation and are re-evaluated immediately before write.

**AA-D21 — Operator-required intents park.** A prepared intent cannot cross a genuine operator-required gate until the exact durable operator decision exists.

**AA-D22 — Controller-only side effect rule.** Provider adapters, workflow completion signals and wake subscriptions SHALL have zero independent repository-write/merge capability. They may only invoke/wake the already-qualified `DSAI_VIT_PHYSICAL_CONTROLLER` path.

**AA-D23 — New autonomous writer identity is operator-required.** If implementation requires a distinct service/GitHub Actions identity with independent write or merge capability, that capability is a new agent/write authority surface and MUST stop for explicit operator approval and qualification.

**AA-D24 — Intent consumption is idempotent.** Duplicate signals/retries/restarts may cause repeated readiness evaluation but at most one effective physical mutation.

## 6. GitHub Actions adapter

**AA-D25 — Provider-neutral core, GitHub first.** GitHub Actions is the first intended provider adapter; GitHub provider semantics never define OVC authority semantics.

**AA-D26 — Exact source binding.** The adapter must bind repository, PR where present, commit/head, workflow, run and check/job identities and conclusion sufficiently to prove which exact future/set it satisfies.

**AA-D27 — Zero chat/session dependency.** Open futures, assurance sets, subscriptions and materialisation intents must be recoverable by a fresh process with no conversation context.

**AA-D28 — Event/reconciliation equivalence is blocking.** Event delivery is an optimization, not the sole liveness source. Fresh-process reconciliation against durable repository/provider state MUST converge to the same logical future/intent state as processing all notifications in order.

**AA-D29 — Missed/duplicate/out-of-order signals are normal inputs.** They must be handled idempotently and may not cause phantom PASS or duplicate merge.

## 7. Failure and race behavior

**AA-D30 — Correctable workflow failure routes to bounded repair.** Content repair creates a new PIP generation and supersedes affected futures/sets/intents.

**AA-D31 — Blocking failure stops only the affected route.** Other authorized lanes continue.

**AA-D32 — Main movement during background assurance is not automatically a rebuild.** AA0 may remain valid; AA1/AA2 renew according to declared dependency/currentness scope.

**AA-D33 — Main movement during an active physical lease retains existing exclusivity semantics.** No weakening of SIQ/VIT lease behavior.

**AA-D34 — Green-to-lease crash is recoverable.** A crash after all required workflows pass but before lease/materialisation must recover the same prepared intent and re-evaluate currentness; it cannot create a phantom completion.

## 8. DEVOBS additions

Canonical DSAI3V Development Latency Receipts SHOULD include when observed:
- `foreground_ci_wait_ms`
- `background_ci_elapsed_ms`
- `ci_development_overlap_ms`
- `speculative_successor_ms`
- `workflow_green_to_materialisation_ms`
- `materialisation_ready_idle_ms`
- `assurance_rerun_count`
- `assurance_reuse_count`
- `descendant_invalidation_count`
- `speculative_work_salvaged_ms`
- `speculative_work_discarded_ms`

Missing values remain `UNAVAILABLE`.

**AA-D35 — Primary effectiveness KPI.** Measure the fraction of required-assurance wall time overlapped with useful lawful development, separately from serialized physical-integration wait.

**AA-D36 — Safety KPIs remain zero-tolerance.** False authority allow, duplicate effective merge, accepted tree mismatch, parallel physical merge and lost mandatory completion receipt remain zero-tolerance.

## 9. Closeout and successor

**AA-D37 — No second foreground closeout wait.** Existing durable DSAI3V sidecar materialisation/completion receipt behavior should close packets without another ordinary base-sensitive development stop.

**AA-D38 — Completion wakes successor automatically.** After AA3 equality and receipt binding, official successor release proceeds under the active mandate unless a real stop condition applies.

## 10. Required qualification fixtures

The implementation cannot activate async wake/materialisation semantics without deterministic coverage of at least:
1. duplicate completion signal;
2. missed signal recovered by reconciliation;
3. out-of-order signals;
4. stale green on superseded head/PIP/VIT generation;
5. `RequiredAssuranceSet` membership change after some checks pass;
6. one required check still running while others pass;
7. required check cancelled/skipped;
8. correctable parent CI failure with selective descendant invalidation;
9. blocking failure in one lane while unrelated lane continues;
10. operator-required gate remains parked after all CI green;
11. negative reachability proving provider adapter cannot merge/write independently;
12. crash after green signal before lease acquisition;
13. crash after lease but before write using existing PMT recovery;
14. main movement after AA0 PASS proving declared evidence reuse only;
15. exact predecessor materialisation promoting a speculative successor without rebuild.

**AA-D39 — Reference behavior outranks optimized/event-driven behavior.** A polling/reconciliation reference path and event-driven optimized path must converge to identical logical future/intent/readiness decisions.

## 11. Implementation/activation boundary

**AA-D40 — No new runtime authority from ratification.** This design authorizes only forward design semantics and creation of a repository-specific conformance implementation plan.

**AA-D41 — Same-controller implementation may remain inside existing execution envelope.** After a separately ratified implementation plan and qualification PASS, implementation may remain within existing DSAI3V general authority only if it reuses the exact existing controller capability, keeps eligible packet classes unchanged, preserves all readiness requirements, adds no writer identity, adds no parallel physical merge and changes no programme-owned authority.

**AA-D42 — Any authority expansion stops.** New writer identity, broader packet class, altered readiness predicate, independent merge token/capability or new irreversible side-effect authority is OPERATOR_REQUIRED.

## 12. Rollback

Disable asynchronous future/intent routing for new packets and return them to the current foreground-wait path. Preserve all futures, signals, assurance sets, intents, DEVOBS evidence, receipts and Git history. No force-push/history rewrite.

## 13. Evaluation amendments incorporated

The independent evaluation returned PASS WITH REQUIRED AMENDMENTS. All six required amendments are incorporated:
- hard controller-only side-effect rule;
- speculative irreversible-side-effect barrier;
- explicit assurance dependency/reuse classification with conservative fallback;
- versioned `RequiredAssuranceSet`;
- blocking event/reconciliation equivalence;
- mandatory race/idempotency/authority fixture surface.

## 14. Ratified design terminal state

`ASYNC_ASSURANCE_DESIGN_RATIFIED_IMPLEMENTATION_PLAN_REQUIRED`

No runtime or GitHub Actions behavior changes from this design record alone. The next lawful step is a repository-specific DSAI3V Async Assurance Conformance Implementation Plan that binds the exact current controller, current workflow surfaces, contracts/schemas/fixtures/tests, DEVOBS additions, qualification ladder, rollback and any activation classification.
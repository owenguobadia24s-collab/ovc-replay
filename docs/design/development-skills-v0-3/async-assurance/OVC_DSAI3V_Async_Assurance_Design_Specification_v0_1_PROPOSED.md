# OVC DSAI3V Async Assurance — Design Specification v0.1 PROPOSED

**Document ID:** `OVC-DSAI3V-ASYNC-ASSURANCE-DESIGN-SPEC-0.1`  
**Programme lineage:** `OVC-DSAI-v0.3` / `OVC-DSAI-VIT-v0.3`  
**Prepared:** 15 August 2026  
**Repository baseline:** `main@4492bc55f9da25f3d8b2f9b1ade4a7d77b88bfeb`  
**Status:** PROPOSED DESIGN AMENDMENT — EVALUATION REQUIRED  
**Authority effect:** NONE. This document changes no runtime authority and does not itself enable autonomous writes.

## 0. Executive design decision

DSAI3V SHALL treat required GitHub Actions assurance as an asynchronous validation dependency, not as a foreground development stop. A packet may remain non-materialisable while its required assurance is running, but its continuous-development mandate remains active and may continue lawful successor construction according to the existing `PacketPredecessorRequirement`, dependency frontier and `BuildAheadBudget`.

Workflow completion SHALL act only as a zero-authority signal that wakes the existing DSAI/VIT materialisation controller. It SHALL NOT itself authorize or perform a merge. Physical materialisation remains governed by the existing closed `MATERIALISATION_READY` predicate, exact prospective-tree qualification, current owner authority, programme-state consistency, GRT, SIQ/exclusive lease, exact predecessor, no-blocker and post-write equality rules.

**Primary design thesis:**

> Workflow execution may gate materialisation, but workflow execution must not pause an otherwise-lawful continuous-development mandate.

This amendment refines the implementation of existing DSAI3-D10, DSAI3-D127…D130, DSAI3-D145…D154 and DSAI3-D210…D218. It does not reopen or replace DSAI3-D1…D310.

## 1. Problem and observed motivation

The live DSAI3V/VIT period demonstrates that repository-wide and exact-head workflows can continue for minutes after packet implementation is ready. Current conversational execution can remain occupied polling those workflows, or can stop and report that a merge may occur after checks pass. That behavior defeats the already-ratified separation between build scheduling and landing scheduling.

Recent repository evidence also shows repeated exact-head reconstruction around lawful main movement. The objective here is not to weaken assurance. It is to move assurance waiting off the critical path of development construction and to cause completion of required assurance to wake the same serialized physical controller automatically.

## 2. Constitutional boundary

### AA-D1 — Assurance is evidence, not authority
A workflow/check result is evidence about an exact candidate generation. PASS cannot create programme authority, gate authority, merge authority or scope.

### AA-D2 — Background does not mean optional
A required background assurance remains mandatory for materialisation. Development may continue while it runs; materialisation may not.

### AA-D3 — Development and materialisation remain separate resources
Build slots may remain productive while assurance or physical integration lags. Exactly one physical materialiser remains effective.

### AA-D4 — Existing reserved boundaries remain reserved
No asynchronous mechanism may cross operator-required programme gates, authority deltas, destructive boundaries, force-push/history rewrite, scientific/Validation/publication/probability/risk/exposure/execution boundaries or other current denials.

### AA-D5 — Physical main remains the court record
Prospective work, workflow PASS, VIT qualification or a prepared merge intent never makes a packet physically effective.

## 3. New normative objects

### 3.1 `AssuranceFuture`

An `AssuranceFuture` is the durable promise that one exact assurance profile is running or has completed for one exact packet/PIP/VIT binding.

Required fields:
- `assurance_future_id`
- `packet_id`
- `payload_id`
- `vit_generation_id` where applicable
- `assurance_profile_id`
- `assurance_class`
- exact `candidate_commit` and/or prospective `tree_id`
- required checks and required-success policy
- provider adapter identity
- state
- workflow/check evidence references
- start/completion timestamps
- dependency/currentness bindings
- `superseded_by` when applicable

States: `CREATED`, `RUNNING`, `PASS`, `FAIL_CORRECTABLE`, `FAIL_BLOCKING`, `STALE`, `CANCELLED`, `SUPERSEDED`, `NOT_EVALUABLE`.

### 3.2 `AssuranceCompletionSignal`

A zero-authority durable signal emitted when one required workflow/check reaches a terminal state. It binds provider, run/check identity, exact candidate/PIP/VIT binding, conclusion and observed completion time.

Duplicate delivery is lawful and MUST be idempotent.

### 3.3 `ConditionalMaterialisationIntent`

A durable pre-authorized intent for an already-authorized packet to request materialisation when, and only when, the full materialisation predicate becomes true.

Required fields:
- `materialisation_intent_id`
- packet/PIP/VIT/train identities
- expected predecessor and result tree
- exact gate/authority manifest
- required `AssuranceFuture` IDs
- required GRT proof identity or future binding
- review/blocker policy
- currentness requirements
- physical materialisation profile
- action: `REQUEST_SERIALIZED_SQUASH_MATERIALISATION`
- state and supersession lineage

States: `PREPARED`, `WAITING_ASSURANCE`, `WAITING_PREDECESSOR`, `WAITING_CURRENTNESS`, `WAITING_LEASE`, `MATERIALISATION_READY`, `CONSUMED`, `BLOCKED`, `CANCELLED`, `SUPERSEDED`.

### 3.4 `AssuranceWakeSubscription`

A durable provider-neutral subscription that maps terminal assurance signals to one or more exact futures/intents and wakes the existing DSAI controller. It grants no repository permission itself.

## 4. Assurance stratification

### AA-D6 — Four operational assurance bands

`AA0_BACKGROUND_REUSABLE` — packet-local/base-independent assurance: unit/fixture/schema/contract tests, deterministic packet checks, runner/parity checks that do not depend on the final physical predecessor, and other evidence explicitly classified base-independent.

`AA1_PROSPECTIVE_TREE_BOUND` — composition/tree-sensitive assurance over an exact prospective VIT generation, including exact resulting-tree tests and GRT/A2 where lawfully available before physical-head position.

`AA2_MATERIALISATION_EDGE` — mutable currentness checks that must be fresh immediately before write: owner authority current, programme-state/current-pointer consistency, required review/blocker state, exact active train placement, exact predecessor, current GRT where required, security allow and SIQ/lease readiness.

`AA3_POST_WRITE_EQUIVALENCE` — post-write observation proving physical tree equality, receipt binding and effective completion.

### AA-D7 — Run early what can be reused
AA0 SHALL begin as soon as the packet generation is stable enough to test. AA1 SHALL begin as soon as the exact prospective tree exists. AA2 SHALL be deferred or renewed near the materialisation frontier. AA3 occurs only after physical write.

### AA-D8 — Reuse is dependency-scoped
Main movement or reorder MUST NOT discard AA0 evidence merely because placement changed. Only evidence whose declared dependency/currentness frontier changed is renewed.

### AA-D9 — Stale green is not green
A PASS bound to a superseded head, payload, VIT generation, authority frontier or other identity-critical binding becomes `STALE`/`SUPERSEDED` for materialisation. It remains historical evidence.

## 5. Continuous successor execution

### AA-D10 — Workflow wait never pauses an active mandate by itself
`AssuranceFuture.RUNNING` SHALL NOT change an otherwise-active continuous mandate to an operator-wait state.

### AA-D11 — Existing speculative successor rules control build-ahead
A successor may enter `SPECULATIVE_RUNNING` only when its existing predecessor/dependency contract permits build-ahead and the current `BuildAheadBudget` admits it.

### AA-D12 — No speculative authority promotion
Speculative work may construct branches/PIPs/VIT generations and run lawful assurance. It may not become physically effective or consume a reserved authority transition early.

### AA-D13 — Exact predecessor landing promotes without rebuild
If the predecessor materialises exactly as qualified and all successor dependency bindings remain valid, existing `SPECULATIVE_RUNNING -> AUTHORITATIVE_RUNNING` behavior applies with no restart.

### AA-D14 — Failed parent causes selective invalidation
A failed assurance or changed payload invalidates descendants only according to the existing dependency/invalidation graph. Unrelated work is preserved.

## 6. Conditional materialisation semantics

### AA-D15 — Intent can be prepared before workflows finish
After implementation/QA preparation, DSAI may persist a `ConditionalMaterialisationIntent` while assurance is still running.

### AA-D16 — Workflow completion wakes; it does not merge
An `AssuranceCompletionSignal` SHALL only trigger controller re-evaluation of the exact intent.

### AA-D17 — Closed readiness remains controlling
The controller may advance to `MATERIALISATION_READY` only when all current DSAI3-D127 readiness conditions are true for the exact generation immediately before write.

### AA-D18 — All required checks must reach terminal PASS
Partial green, queued checks, skipped-required checks, cancelled-required checks or unavailable evidence cannot satisfy the intent.

### AA-D19 — Operator-required intents park
For an operator-required gate, an intent may be prepared but MUST remain `WAITING_OPERATOR`/non-materialisable until the exact operator decision is durable.

### AA-D20 — Existing controller identity owns the side effect
The provider signal adapter SHALL NOT receive independent merge authority. It wakes the already-authorized `DSAI_VIT_PHYSICAL_CONTROLLER`, which owns the same existing serialized squash-materialisation policy.

### AA-D21 — A new autonomous writer identity would be a new authority surface
If implementation requires a new GitHub Actions/service identity with independent repository-write or merge capability rather than invoking the existing controller capability, that activation is OPERATOR_REQUIRED and must be separately qualified.

### AA-D22 — Intent consumption is idempotent
Repeated signals, retries or controller restarts MUST result in at most one effective physical packet mutation.

## 7. Provider and GitHub Actions boundary

### AA-D23 — Provider-neutral core
The normative design is provider-neutral. GitHub Actions is the first expected adapter, but GitHub workflow semantics do not define OVC authority semantics.

### AA-D24 — Exact source binding
A GitHub Actions adapter must bind repository, PR, commit/head, workflow, run, check/job identities and conclusion sufficiently to prove which `AssuranceFuture` the result satisfies.

### AA-D25 — No chat/session dependency
Workflow completion and intent wakeup must be durable and reconstructable with no open ChatGPT conversation. A fresh controller process must recover open futures, subscriptions and intents and choose the same next lawful action.

### AA-D26 — Missed event recovery
If a completion notification is lost, periodic/restart reconciliation may discover the terminal workflow state and emit the same logical signal idempotently.

## 8. Failure and race handling

### AA-D27 — Correctable CI failure routes to repair
`FAIL_CORRECTABLE` reopens the packet generation for bounded repair; any content change produces a new PIP generation and supersedes affected futures/intents.

### AA-D28 — Blocking failure stops the affected route, not unrelated lanes
`FAIL_BLOCKING`, security deny or authority invalidation blocks/quarantines the affected packet according to existing DSAI rules while unrelated authorised lanes continue.

### AA-D29 — Main movement during background assurance is not automatically a rebuild
Base-independent evidence remains reusable. Prospective-tree/currentness evidence is recomputed only where the movement changes its declared dependency frontier.

### AA-D30 — Main movement during active physical lease remains an exclusivity event
This amendment does not weaken existing SIQ/VIT physical lease rules.

## 9. DEVOBS effectiveness measurements

Every canonical DSAI3V completion latency receipt SHOULD add, when observed:
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

Missing telemetry remains `UNAVAILABLE`; no value is inferred.

### AA-D31 — Primary effectiveness KPI
The primary operational KPI is the fraction of assurance wall time overlapped with useful lawful development, separated from physical serialized integration wait.

### AA-D32 — Safety KPIs remain zero-tolerance
False authority allow, duplicate effective merge, physical/VIT tree mismatch accepted as success, parallel physical merge and lost mandatory completion receipt remain zero-tolerance.

## 10. Closeout and successor behavior

### AA-D33 — No second foreground closeout wait
Where DSAI3V already supports durable sidecar materialisation/completion receipts, post-merge closeout SHALL not create another ordinary base-sensitive development stop.

### AA-D34 — Completion wakes successor automatically
After AA3 equality and receipt binding, packet completion and official successor release continue automatically under the existing mandate unless a real stop condition applies.

## 11. Activation and implementation handoff

The implementation plan SHALL contain at least:
1. exact contracts/schemas for the four new objects;
2. provider-neutral future/intent state machines;
3. GitHub Actions signal adapter or equivalent reconciliation mechanism;
4. reuse of the existing DSAI physical controller rather than a second merge authority;
5. focused synthetic race/idempotency/stale-signal/failure fixtures;
6. live shadow proving workflow-completion wake decisions without physical side effects;
7. exact qualification that required assurance still blocks materialisation while no longer blocking development construction;
8. DEVOBS field extension and comparison receipt;
9. rollback to foreground-wait routing without evidence deletion.

### AA-D35 — Activation classification
If the implementation merely changes wake/scheduling semantics inside the already-active DSAI3V default controller and does not create a new writer identity, broaden packet classes or weaken the closed materialisation predicate, activation may remain within the existing already-authorized DSAI3V execution envelope after a ratified implementation plan and qualification PASS. Any new autonomous writer identity, expanded merge capability or altered authority predicate is OPERATOR_REQUIRED.

### AA-D36 — Rollback
Rollback disables asynchronous future/intent routing for new packets and returns them to the current foreground-wait execution path. Existing workflow evidence, futures, intents, receipts and Git history remain preserved; no force-push/history rewrite.

## 12. Proposed design terminal state

`ASYNC_ASSURANCE_DESIGN_COMPLETE_PENDING_EVALUATION`

No runtime is changed by this document. The next lawful step is independent design evaluation, bounded revision if required, operator ratification, then a repository-specific conformance implementation plan.
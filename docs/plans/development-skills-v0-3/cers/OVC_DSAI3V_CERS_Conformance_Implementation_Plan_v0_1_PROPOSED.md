# OVC DSAI3V CERS — Conformance Implementation Plan v0.1 PROPOSED

**Plan ID:** `OVC-DSAI3V-CERS-CONFORMANCE-IMPLEMENTATION-PLAN-0.1`  
**Programme ID:** `OVC-DSAI3V-CERS-CONFORMANCE-v0.1`  
**Governing design:** `OVC-DSAI3V-CERS-DESIGN-SPEC-0.1-R1-RATIFIED`  
**Repository baseline:** `main@9351a0d900064f948f78859e26d12443c04dad6c` / tree `45ed60f1a7667d52741d78e51c780fa8d6803eb2`  
**Prepared:** 18 August 2026  
**Status:** PROPOSED FOR PLAN REVIEW  
**Authority effect:** Proposed bounded inactive/shadow implementation only. Live unattended dispatch denied.

## 0. Purpose

Implement and qualify the repository-specific Continuous Execution Reconciler / Supervisor required to make DSAI3V continuous execution host-independent and restart-safe, while preserving existing programme authority, Async Assurance, VIT/SIQ physical serialization, GRT and DEVOBS.

The plan must close the exact gap between `DECISION_SELECTED` / durable `START_SUCCESSOR` and **observed worker execution**.

## 1. Source precedence

1. current repository `main`;
2. programme-owned authority/current state;
3. active `DEFAULT_EXECUTION_SUBSTRATE`;
4. DSAI v0.3 continuous-execution plan;
5. ratified Async Assurance design/implementation/activation;
6. VIT/SIQ/GRT contracts;
7. `OVC-DSAI3V-CERS-DESIGN-SPEC-0.1-R1-RATIFIED`;
8. this plan where consistent with 1–7.

Missing state or authority is never inferred.

## 2. Implementation boundary

Allowed before live activation:
- contracts/schemas/registries;
- registered programme discovery;
- deterministic reconciliation;
- supervisor lease/fencing;
- durable dispatch transaction state;
- executor capability declarations;
- shadow/non-writing executor adapter;
- read-only provider reconciliation;
- tests/fixtures/adversarial simulations;
- DEVOBS;
- QA/gate packets.

Denied before `CERS-G-LIVE-DISPATCH`:
- waking a repository-writing worker after foreground chat/process termination;
- new autonomous writer identity;
- any direct main write/merge;
- parallel physical merge;
- force-push/history rewrite;
- programme authority expansion;
- scientific/Validation/publication/probability/risk/exposure/execution authority.

## 3. Work packets

### CERS-WP0 — source, authority and liveness-gap freeze
Materialise exact source census and current authority boundary:
- DSAI3V default substrate/controller/gateway;
- Async Assurance live authority/profile;
- VIT/SIQ/GRT currentness surfaces;
- current ORCH automatic selection behavior;
- persistent runtime/chat-drainage semantics;
- exact live-dispatch denial.

Gate `CERS-G0`: AUTO_RATIFIABLE, delta `NONE`.

### CERS-WP1 — contracts, schemas and registries
Implement:
`ReconciliationSnapshot`, `RunnableWorkItem`, `RunnableWorkSet`, `ExecutorCapabilityRecord`, `SupervisorLease`, `DispatchIdentity`, `DispatchTransaction`, `WorkerOwnership`, `QuiescenceControl`, `SupervisorCheckpoint`, action/side-effect/reason registries, programme-root registry.

Gate `CERS-G1`: AUTO_RATIFIABLE, inactive contracts only.

### CERS-WP2 — deterministic reference reconciler
Implement pure side-effect-free reconciliation from repository/provider observations to exact snapshot, runnable set, reason-coded non-runnable set and candidate dispatch identities. No dispatch occurs.

Gate `CERS-G2`: AUTO_RATIFIABLE.

### CERS-WP3 — supervisor ownership and recovery
Implement fencing, event + sweep convergence, bounded backoff, dispatch crash recovery, heartbeat/reclaim and quiescence. Still no live repository-writing dispatch.

Gate `CERS-G3`: AUTO_RATIFIABLE.

### CERS-WP4 — shadow executor and build-ahead proof
Implement one non-writing fixture/sandbox executor adapter proving exact dispatch identity, observed start acknowledgement, heartbeat, duplicate suppression, speculative successor scheduling, selective invalidation and failure routing. No main mutation.

Gate `CERS-G4`: AUTO_RATIFIABLE.

### CERS-WP5 — adversarial qualification and DEVOBS
Run full CERS catalogue including split-brain, crash windows, missed/duplicate events, stale workers, provider outage, operator HOLD, pointer conflicts, rollback and no-runnable-idle-without-reason. Emit live activation packet.

Gate `CERS-G5`: AUTO_RATIFIABLE only if zero-tolerance safety and liveness conditions pass.

### CERS-G-LIVE-DISPATCH — activate unattended dispatch
**OPERATOR_REQUIRED.** Exact executor identity and capabilities must be named.

### CERS-WP6 — bounded live pilot
Only after operator PASS; exact programme/action allowlist and stop conditions frozen before execution.

### CERS-G6 — post-activation effectiveness
AUTO-ratifiable only if the bounded pilot proves the exact approved behavior with zero safety violations.

## 4. Required tests

All design fixtures plus schema validation, identity determinism, current-pointer integrity, conservative action fallback, capability negative reachability, no heuristic programme discovery, no direct-main capability, duplicate-start exclusion, fencing across restart and deterministic fairness/backpressure.

## 5. Branch and integration discipline

- one bounded branch per packet/group;
- WP1–WP5 may be grouped only if inactive/shadow and each logical gate remains separately evidenced;
- latest lawful main before permanent candidate;
- VIT lineage mandatory;
- required CI/QA/GRT/SIQ/merge-readiness;
- correctable defects repaired in scope;
- no force-push/history rewrite;
- no live dispatch before operator gate.

## 6. Rollback

Before live activation, forward-disable shadow surfaces while preserving evidence. After activation, set `DISABLE_NEW_DISPATCH`, drain/cancel according to packet contracts and restore explicit foreground dispatch for new work. Preserve all court records.

## 7. Target state

`CERS_IMPLEMENTED_QUALIFIED_INACTIVE_OR_SHADOW / CERS-G-LIVE-DISPATCH GATE_READY`

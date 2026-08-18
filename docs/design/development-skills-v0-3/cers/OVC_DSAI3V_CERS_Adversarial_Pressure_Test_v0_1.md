# Adversarial Pressure-Test and Review — OVC DSAI3V CERS v0.1

**Review ID:** `OVC-DSAI3V-CERS-PRESSURE-TEST-0.1`  
**Evaluated design:** `OVC-DSAI3V-CERS-DESIGN-SPEC-0.1`  
**Repository baseline:** `main@9351a0d900064f948f78859e26d12443c04dad6c`  
**Review date:** 18 August 2026  
**Decision:** PASS WITH REQUIRED AMENDMENTS  
**Authority effect:** NONE

## 0. Review method

This review attacks the proposed CERS design against current DSAI3V, VIT/SIQ, Async Assurance, ORCH-3/4/5 and repository-state semantics. It focuses on the exact failure mode the programme is intended to solve: development going idle because a conversational invocation ends or waits on GitHub despite lawful successor work existing.

The review does not grant live unattended dispatch authority.

## 1. Overall finding

The architecture is necessary and correctly placed as a liveness layer rather than a second authority or merge controller. The current repository already has:
- persistent mandate reconstruction;
- background assurance futures/reconciliation;
- ordered VIT/SIQ physical integration;
- automatic ORCH selection;
- zero-chat-dependency design requirements.

The design closes the remaining gap only if it proves **real execution actuation**, not merely another layer that emits `DECISION_SELECTED`.

The first draft is therefore acceptable only with the amendments below.

## 2. Findings

### PT-CERS-01 — Missing distinction between logical liveness and worker liveness — REQUIRED AMENDMENT

A supervisor can repeatedly decide `DISPATCHABLE` while no execution worker is actually capable of starting. That would reproduce the present failure under a new name.

**Required revision:** define `ExecutorCapabilityRecord`, start acknowledgement, worker heartbeat and a liveness condition that distinguishes `intent persisted` from `execution observed`.

### PT-CERS-02 — Lease expiry alone is insufficient — REQUIRED AMENDMENT

Clock/lease expiry does not prevent an old partitioned supervisor from continuing to send writes.

**Required revision:** require fencing generations/tokens validated at every dispatch and worker ownership transition. Stale fence acceptance is zero tolerance.

### PT-CERS-03 — Programme discovery can accidentally infer authority — REQUIRED AMENDMENT

Scanning arbitrary files/PR names for apparent `READY` work could create implicit portfolio authority.

**Required revision:** CERS may enumerate only explicit registered programme-state/current-pointer roots and owner-authorized packet records. Unknown/unregistered programmes are non-dispatchable.

### PT-CERS-04 — Dispatch idempotency must be stronger than wake idempotency — REQUIRED AMENDMENT

Duplicate wake handling does not by itself prevent two worker starts.

**Required revision:** add a content-addressed `DispatchIdentity` and at-most-one authoritative `START_ACKNOWLEDGED` transition per packet generation/fencing generation, with deterministic retry reuse.

### PT-CERS-05 — Recovery sweep needs bounded backoff and starvation detection — REQUIRED AMENDMENT

A periodic reconciler can become either a tight poller or silently back off forever.

**Required revision:** implementation plan must define bounded configurable recovery cadence/backoff policy, provider-rate-limit behavior and `runnable_idle` starvation alerting. Exact numeric cadence remains operational, not invented in design.

### PT-CERS-06 — Unattended writer activation is a real authority boundary — PASS / HARD BOUNDARY

The design correctly identifies that waking a repository-writing worker after the chat ends is not merely read-only reconciliation. It is activation of a deferred unattended capability and may involve agent/write authority.

**Required preservation:** all implementation through shadow qualification must remain non-authoritative for live unattended dispatch; exact executor identity/capabilities must be named at `CERS-G-LIVE-DISPATCH`.

### PT-CERS-07 — Speculative side-effect barrier is correct but must bind action classes — REQUIRED AMENDMENT

“Reversible work” is too semantic if not machine-classified.

**Required revision:** introduce explicit `DispatchActionClass` / `side_effect_class` with conservative fallback to `IRREVERSIBLE_OR_UNKNOWN`, which blocks speculative dispatch.

### PT-CERS-08 — Physical integration separation — PASS

The design properly leaves physical-main actuation with VIT/SIQ and prohibits a second merge controller.

### PT-CERS-09 — Event/reconciliation equivalence — PASS WITH HARDENING

The event + sweep model is sound.

**Required revision:** qualification must include a reference pure-reconciliation path and prove convergence of snapshot, runnable set, intents and outcomes under missed/duplicate/out-of-order wakes.

### PT-CERS-10 — Crash windows need explicit transaction model — REQUIRED AMENDMENT

Crashes between intent persistence, provider dispatch, start acknowledgement, worker branch mutation and outcome persistence can create ambiguous “did it start?” states.

**Required revision:** define `DispatchTransaction` phases and recovery dispositions, including `UNKNOWN_START_STATE` that requires reconciliation rather than blind redispatch.

### PT-CERS-11 — Supervisor must not own programme repair semantics — REQUIRED AMENDMENT

If CERS interprets a test failure itself, it can become a policy engine.

**Required revision:** CERS routes failures to existing programme/DSAI bounded repair semantics; it does not invent remediation or weaken tests.

### PT-CERS-12 — Human/operator stop responsiveness — REQUIRED AMENDMENT

A persistent supervisor needs a durable way to stop new dispatches quickly.

**Required revision:** define a global/per-programme `QuiescenceControl` with `RUN`, `DRAIN`, `HOLD`, `DISABLE_NEW_DISPATCH`; operator-owned HOLD always dominates automated wake.

## 3. Required amendments

The revised design and implementation plan must incorporate all of:

1. `ExecutorCapabilityRecord` and observed start/heartbeat semantics.
2. Fencing-token validation at every dispatch/ownership transition.
3. Explicit registered programme-discovery roots; no heuristic authority inference.
4. Content-addressed dispatch identity and duplicate-start prevention.
5. Bounded recovery/backoff + runnable-idle/starvation observability.
6. Live unattended dispatch remains operator-required with exact executor identity.
7. Machine-readable action/side-effect classification; unknown => irreversible/deny speculative.
8. Reference reconciliation convergence test.
9. `DispatchTransaction` with `UNKNOWN_START_STATE` recovery.
10. Failure routing to existing repair owners only.
11. Durable `QuiescenceControl`.

## 4. Decision

**PASS WITH REQUIRED AMENDMENTS.**

The proposal addresses a genuine architectural liveness gap and is consistent with DSAI3V when it remains a supervisor of existing authority rather than a source of authority. Incorporate PT-CERS-01 through PT-CERS-12, then ratify the revised design and use it to produce a repository-specific conformance implementation plan.

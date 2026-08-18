# Adversarial Plan Review — OVC DSAI3V CERS Conformance v0.1

**Review ID:** `OVC-DSAI3V-CERS-PLAN-REVIEW-0.1`  
**Reviewed plan:** `OVC-DSAI3V-CERS-CONFORMANCE-IMPLEMENTATION-PLAN-0.1`  
**Governing design:** `OVC-DSAI3V-CERS-DESIGN-SPEC-0.1-R1-RATIFIED`  
**Repository baseline:** `main@9351a0d900064f948f78859e26d12443c04dad6c`  
**Decision:** PASS WITH REQUIRED AMENDMENTS  
**Authority effect:** NONE

## 1. Overall assessment

The proposed packet sequence is coherent and preserves the live-dispatch boundary, but it needs more precise implementation gates so that shadow qualification cannot accidentally become unattended repository-writing actuation.

## 2. Required amendments

### PR-CERS-01 — Split WP4 executor proof into capability proof and side-effect proof
WP4 must require an explicit fixture-only/non-writing adapter and a negative capability assertion for repository writes, merge, force-push and irreversible effects. Any real branch-write executor remains outside WP4.

### PR-CERS-02 — Add registered programme-root census to WP0
The first packet must freeze exactly how CERS discovers programme state and prove no heuristic filesystem/PR/chat discovery.

### PR-CERS-03 — Add reference model artifact
WP2 must emit a deterministic reference reconciliation result that is later used as the oracle for event-driven optimization.

### PR-CERS-04 — Add fencing/unknown-start fatality conditions
WP3/G3 must fail if stale fencing can be accepted, if ambiguous start can be blindly retried, or if duplicate start cannot be excluded.

### PR-CERS-05 — Add liveness effectiveness criterion to G5
Safety PASS alone is insufficient. G5 must demonstrate in fixture/shadow that runnable work advances while background assurance remains running and the foreground caller is absent.

### PR-CERS-06 — Activation packet must distinguish existing-controller wake from new worker authority
The gate must explicitly classify:
- `EXISTING_QUALIFIED_EXECUTOR_IDENTITY`, or
- `NEW_EXECUTOR_IDENTITY_REQUIRES_AGENT_WRITE_AUTHORITY`.

No generic “supervisor active” approval is sufficient.

### PR-CERS-07 — Add rollback rehearsal before live gate
WP5 must exercise `DISABLE_NEW_DISPATCH` / drain behavior and prove restart to foreground-only mode without lost state.

### PR-CERS-08 — Add bounded live pilot stop conditions
WP6 must stop immediately on duplicate start, stale-fence acceptance, unexplained runnable idle beyond policy, direct-main reachability, operator-boundary false allow or non-reproducible completion evidence.

## 3. Decision

**PASS WITH REQUIRED AMENDMENTS.**

No architectural redesign is required. Incorporate PR-CERS-01 through PR-CERS-08 into REVISED 1, then ratify the plan. The plan may authorize WP0–WP5 inactive/shadow conformance work. `CERS-G-LIVE-DISPATCH` remains operator-required.

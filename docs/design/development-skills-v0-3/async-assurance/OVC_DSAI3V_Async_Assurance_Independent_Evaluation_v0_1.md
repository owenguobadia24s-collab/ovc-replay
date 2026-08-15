# Independent Design Evaluation — DSAI3V Async Assurance v0.1

**Evaluation ID:** `OVC-DSAI3V-ASYNC-ASSURANCE-EVALUATION-0.1`  
**Evaluated design:** `OVC-DSAI3V-ASYNC-ASSURANCE-DESIGN-SPEC-0.1`  
**Repository baseline observed:** `main@4492bc55f9da25f3d8b2f9b1ade4a7d77b88bfeb`  
**Evaluation status:** PASS WITH REQUIRED AMENDMENTS  
**Authority effect:** NONE

## 0. Scope and method

This evaluation checks the proposed amendment against the ratified DSAI v0.3/VIT constitution, the ratified VIT implementation plan, the active DSAI3V default-execution-substrate record and current live repository behavior. It evaluates execution safety, authority preservation, idempotency, currentness, failure handling, restartability, practical latency impact and observability completeness. It does not grant runtime authority.

## 1. Overall assessment

The proposal is directionally correct and strongly aligned with the existing DSAI3V constitution. The core change is not a relaxation of CI or merge safety; it is a control-flow correction that moves workflow waiting out of the foreground development critical path while retaining all required checks as preconditions for physical materialisation.

The design should proceed, but six amendments are required before ratification to avoid creating a de-facto second merge controller, overstating assurance reusability, or allowing speculative work to consume irreversible side effects.

## 2. Conformance findings

### E-AA-01 — Strong alignment with existing VIT semantics — PASS

The amendment correctly operationalizes existing separation of build and landing capacity, active `WAITING_INTEGRATION`, speculative successor execution, reuse of unaffected assurance and the closed `MATERIALISATION_READY` predicate. It does not require reopening DSAI3-D1…D310.

### E-AA-02 — Workflow PASS must remain zero-authority — PASS

The proposed `AssuranceCompletionSignal` is correctly defined as evidence only. This is essential because the active default substrate already requires owner authority, programme-state consistency, QA, GRT, SIQ exact-final assurance, tree equality and complete receipts; a provider check conclusion cannot replace those controls.

### E-AA-03 — New writer identity risk — REQUIRED AMENDMENT

The first draft permits a GitHub Actions adapter but must be stronger: an adapter may not hold independent merge/write capability merely for convenience. The only non-reserved implementation path is to wake the existing qualified DSAI physical controller. If a new background service or GitHub workflow identity needs independent repository-write capability, that is a new agent/write authority surface and requires an explicit operator gate.

**Required revision:** elevate this from implementation guidance to a hard constitutional rule and include a negative-reachability fixture.

### E-AA-04 — Speculative successor side effects need a hard barrier — REQUIRED AMENDMENT

The draft correctly restricts physical materialisation, but speculative successor construction could still trigger irreversible external side effects such as publication, provider intake, external durable writes or programme-owned actions if an implementation equates “build” with “execute all packet steps.”

**Required revision:** `SPECULATIVE_RUNNING` may perform only reversible/local/repository-branch/VIT work already permitted by the successor’s authority. Any irreversible external side effect requires authoritative predecessor satisfaction and its own existing authority.

### E-AA-05 — Assurance classification must be declared, not inferred — REQUIRED AMENDMENT

Whether a test is base-independent, prospective-tree-bound or currentness-sensitive cannot be guessed from workflow names. Misclassification could reuse invalid evidence.

**Required revision:** every assurance profile/check must carry an explicit `dependency_scope` / `reuse_class`; unknown classification defaults to materialisation-sensitive/no reuse.

### E-AA-06 — Aggregate workflow success must be exact — REQUIRED AMENDMENT

A packet often has several workflows/jobs. One green workflow cannot release the intent while another required check is queued, skipped, cancelled or running.

**Required revision:** add `RequiredAssuranceSet` semantics with exact required members, terminal-state policy and versioned membership. Set changes supersede the intent.

### E-AA-07 — Event delivery cannot be sole liveness mechanism — REQUIRED AMENDMENT

Provider notifications can be duplicated, delayed or missed. The proposed missed-event recovery is correct but should be blocking for qualification rather than optional.

**Required revision:** require event + reconciliation equivalence: a fresh process that only queries durable provider/repository state must converge to the same future/intent state.

### E-AA-08 — Correct distinction between CI wait and physical integration wait — PASS

The DEVOBS additions are well chosen. `foreground_ci_wait_ms`, `ci_development_overlap_ms`, `workflow_green_to_materialisation_ms` and `materialisation_ready_idle_ms` will separate saved development latency from irreducible serialized landing latency.

### E-AA-09 — Live evidence supports the need — PASS

Recent repository operation provides concrete motivating examples. PR #901 was a no-authority administrative closeout that became mergeable only after its workflows completed, requiring an explicit later interaction to finish. C2P2-WP6 recorded two current-main requeues around lawful main movement before landing. These observations do not constitute a complete performance audit, but they are sufficient to justify a bounded control-flow hardening experiment.

### E-AA-10 — No safety reason for foreground chat polling — PASS

No constitutional requirement says the conversational agent must remain blocked while GitHub-hosted assurance executes. Durable futures, wake subscriptions and restart-equivalent controller state are a better fit with the existing zero-chat-dependency requirement.

## 3. Required amendments

The following amendments are mandatory for ratification:

1. **Controller-only side effect rule.** Provider adapters/signals have zero write/merge capability; new writer identity => operator gate.
2. **Speculative irreversible-side-effect barrier.** Speculative successor work cannot consume irreversible external effects or reserved actions before authoritative predecessor satisfaction.
3. **Explicit assurance dependency/reuse classification.** Unknown => conservative no-reuse/materialisation-sensitive.
4. **`RequiredAssuranceSet`.** Versioned complete set of required futures/checks; all must satisfy exact terminal PASS policy.
5. **Event/reconciliation equivalence.** Missed/duplicate/out-of-order provider notifications must converge deterministically from durable state.
6. **Qualification fixtures.** At minimum: duplicate signal, missed signal, stale green on superseded head, required-check membership change, parent CI failure with descendant selective invalidation, operator-required gate remaining parked, new-writer negative reachability and crash between green signal and lease acquisition.

## 4. Authority assessment

The design amendment itself has `authority_effect=NONE` and can be ratified as forward execution semantics. Runtime implementation remains separately governed.

A future implementation may remain inside the already-active DSAI3V default execution envelope only if it:
- reuses the exact existing DSAI physical controller identity/capability;
- does not add a new writer/merge identity;
- does not broaden eligible packet/gate classes;
- does not weaken or remove any required assurance/currentness/GRT/SIQ/tree-equality condition;
- does not permit parallel physical merge;
- does not change programme-owned authority.

Otherwise a new operator-required activation gate is necessary.

## 5. Evaluation decision

**PASS WITH REQUIRED AMENDMENTS.**

The amendment solves a real implementation mismatch between ratified continuous-execution semantics and current foreground workflow waiting. The identified issues are precision/safety hardening, not architectural contradictions. Incorporate E-AA-03 through E-AA-07 and the required fixture surface, then ratify the revised design without reopening DSAI3-D1…D310.
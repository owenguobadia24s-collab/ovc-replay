# OVC DSAI3V Async Assurance — Conformance Implementation Plan v0.1 RATIFIED

**Plan ID:** `OVC-DSAI3V-ASYNC-ASSURANCE-CONFORMANCE-IMPLEMENTATION-PLAN-0.1-RATIFIED`  
**Programme ID:** `OVC-DSAI3V-ASYNC-ASSURANCE-CONFORMANCE-v0.1`  
**Architecture lineage:** `OVC-DSAI-v0.3` / `OVC-DSAI-VIT-v0.3`  
**Governing design:** `OVC-DSAI3V-ASYNC-ASSURANCE-DESIGN-SPEC-0.1-R1-RATIFIED`  
**Prepared / operator-ratified:** 15 August 2026  
**Repository baseline:** `main@1bdeec9c8697b302170f72dc0d03129c6223cf06`  
**Status:** RATIFIED — REPOSITORY MATERIALISATION / IMPLEMENTATION AUTHORISED; LIVE ASYNC ACTIVATION RESERVED  
**Authority effect:** bounded implementation, schemas/contracts/fixtures/tests, deterministic provider normalization, durable reconciliation, inactive/shadow controller wake integration, DEVOBS observability and qualification. No new writer/merge identity and no live async activation from this plan alone.

## 0. Ratified implementation decision

Implement the repository-specific Async Assurance machinery required by the repository-effective DSAI3V design. GitHub Actions assurance SHALL become representable as durable asynchronous futures and exact versioned assurance sets. Running assurance SHALL not be modeled as an operator wait or development-stop condition. Workflow terminal observations SHALL have zero authority and may only update durable assurance evidence and request re-evaluation by the existing `DSAI_VIT_PHYSICAL_CONTROLLER` path.

This plan deliberately separates **implementation/qualification** from **live activation**. Implementation through AA-WP5 is authorized by this ratification. A later consolidated `DSAI3V-AA-G-ACTIVATE` gate is OPERATOR_REQUIRED before changing the active default substrate to consume asynchronous wake/materialisation semantics in live development. If implementation demonstrates that activation would require a new autonomous writer/service identity or independent GitHub merge token, that exact authority delta MUST be included in the activation packet and remains denied until operator PASS.

Primary invariant:

> Required assurance may block physical materialisation, but running assurance must not block otherwise-lawful development construction.

## 1. Source precedence and court-record rule

1. Repository `main` and accepted operator decisions control current authority, active services and implementation state.
2. The repository-effective Async Assurance design controls AA-D1…AA-D42 semantics.
3. The ratified DSAI v0.3/VIT design and VIT conformance plan control prospective-tree, dependency, invalidation, materialisation and recovery semantics.
4. `registries/authority/DEFAULT_EXECUTION_SUBSTRATE.json` controls the currently active execution envelope.
5. Existing GRT/SIQ contracts remain controlling for exact-tree/currentness/serialized physical integration.
6. Existing DEVOBS canonical DSAI3V completion receipt remains the mandatory completion-observability envelope.
7. This plan controls only repository-specific materialisation, implementation, tests, qualification and activation routing where consistent with 1–6.

Missing implementation, schema, fixture, provider binding, qualification evidence or authority is never inferred.

## 2. Current baseline and implementation boundary

At plan ratification the active default substrate names `DSAI_VIT_PHYSICAL_CONTROLLER`, routes already-authorized `AUTO_EXECUTABLE` / `AUTO_RATIFIABLE` packets with `authority_delta=NONE`, requires programme-state consistency and canonical DEVOBS completion receipts, and keeps physical writes serialized through `DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY` with `parallel_physical_merge=false`.

The repository contains logical VIT/materialisation/runtime primitives and durable completion receipts. It does not, from the evidence available at this baseline, establish an independently-running GitHub Actions identity with autonomous repository merge authority. This plan therefore implements a **zero-write provider adapter** and a **controller-wake request surface**, not a second writer.

## 3. Canonical implementation surface

The implementation SHALL materialise and test the following exact concepts:

- `AssuranceFuture`
- `AssuranceCompletionSignal`
- `RequiredAssuranceSet`
- `ConditionalMaterialisationIntent`
- `AssuranceWakeSubscription`
- durable `AsyncAssuranceStore`
- deterministic `GitHubAssuranceObservation` normalization
- event-driven observation application and durable reconciliation reference path
- controller-only `MaterialisationWakeRequest`
- explicit assurance classification: `AA0_BACKGROUND_REUSABLE`, `AA1_PROSPECTIVE_TREE_BOUND`, `AA2_MATERIALISATION_EDGE`, `AA3_POST_WRITE_EQUIVALENCE`
- dependency/reuse classification with unknown/missing => AA2 / no reuse
- stale/superseded green handling
- selective descendant invalidation
- speculative irreversible-side-effect barrier
- DEVOBS Async Assurance metrics

The provider adapter and wake-request surface MUST contain no repository-write, merge, force-push, publication, provider-intake or other irreversible side-effect capability.

## 4. Work packets and gates

### AA-WP0 — plan/court-record materialisation

Materialise this exact ratified plan, operator ratification record, programme state and current pointer.

**Authority:** AUTO_EXECUTABLE after the operator instruction `Create, ratify and implement a repository-specific DSAI3V Async Assurance Conformance Implementation Plan`.  
**Delta:** `PLAN_AND_PROGRAMME_MATERIALISATION_ONLY`.  
**Acceptance:** exact plan/design lineage; active default-substrate binding recorded; live activation explicitly denied; current repository assurance PASS; QA PASS; no unresolved review.  
**Gate:** `DSAI3V-AA-G0` — delegated PASS when acceptance holds.

### AA-WP1 — contracts, schemas and durable state

Implement typed deterministic objects, content-addressed identities, state transitions, versioned RequiredAssuranceSet membership, durable state save/load and restart recovery.

**Delta:** `INACTIVE_ASYNC_ASSURANCE_CONTRACTS`.  
**Gate:** `DSAI3V-AA-G1` AUTO-RATIFIABLE.

### AA-WP2 — GitHub provider normalization and reconciliation

Implement a read-only GitHub observation adapter accepting exact repository/head/workflow/run/job/check conclusions and applying them idempotently to futures. Implement a polling/durable-state reference reconciliation path that converges with ordered event processing.

**Delta:** `READ_ONLY_ASSURANCE_PROVIDER_ADAPTER`.  
**Hard deny:** provider adapter cannot merge/write.  
**Gate:** `DSAI3V-AA-G2` AUTO-RATIFIABLE.

### AA-WP3 — controller wake/readiness integration

Implement `ConditionalMaterialisationIntent` evaluation and `MaterialisationWakeRequest` generation for the existing controller identity. The runtime SHALL re-evaluate owner authority, exact required-assurance set, programme-state/current-pointer consistency, blocker/review state, GRT/currentness bindings, expected predecessor, security and SIQ/lease prerequisites. This packet SHALL NOT perform a physical merge.

**Delta:** `INACTIVE_CONTROLLER_WAKE_CAPABILITY`.  
**Gate:** `DSAI3V-AA-G3` AUTO-RATIFIABLE.

### AA-WP4 — speculative continuation, invalidation and recovery

Bind async-running state to continuous-development semantics: `RUNNING` assurance alone is non-blocking; lawful successors may remain/build `SPECULATIVE_RUNNING` only under existing dependency and build-ahead rules; irreversible side effects remain barred; exact predecessor landing promotes without rebuild when dependencies remain valid; parent failure causes selective invalidation; restart recovers futures/intents without chat state.

**Delta:** `INACTIVE_ASYNC_CONTINUATION_CAPABILITY`.  
**Gate:** `DSAI3V-AA-G4` AUTO-RATIFIABLE.

### AA-WP5 — DEVOBS, adversarial qualification and shadow proof

Extend canonical DSAI3V DEVOBS completion receipts with optional observed Async Assurance metrics while preserving `UNAVAILABLE` for absent telemetry. Run all mandatory design fixtures and reference-vs-optimized reconciliation equivalence. Exercise the implementation in non-authoritative shadow/reconciliation mode only.

Required metrics when observed:
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

**Delta:** `QUALIFIED_INACTIVE_ASYNC_ASSURANCE_CAPABILITY`.  
**Gate:** `DSAI3V-AA-G5` AUTO-RATIFIABLE if all zero-tolerance and qualification conditions pass.

### Grouping authority

AA-WP1 through AA-WP5 MAY be executed as one bounded grouped implementation packet/PR (`DSAI3V-AA-GROUP-CORE`) because they form one inseparable inactive/shadow implementation surface, share the same `authority_delta` envelope, and no packet activates live async materialisation. Each logical packet/gate and its acceptance evidence must nevertheless remain separately represented in programme state and QA.

## 5. Mandatory qualification catalogue

Before `DSAI3V-AA-G5` PASS the implementation MUST prove at least:

1. duplicate completion signal => idempotent state;
2. missed signal => recovered by durable reconciliation;
3. out-of-order signals => deterministic convergence;
4. stale green on superseded head/PIP/VIT => cannot satisfy current intent;
5. RequiredAssuranceSet membership change => new set + superseded intent;
6. one required member running => not materialisation ready;
7. required cancelled/skipped member => not ready;
8. correctable parent failure => selective affected-descendant invalidation;
9. one lane blocking failure => unrelated lane remains runnable;
10. operator-required gate => parks despite all CI green;
11. provider adapter negative reachability => no merge/write capability;
12. crash after green before lease => recovered intent, no phantom completion;
13. lease-before-write crash => existing PMT recovery semantics preserved;
14. main movement after AA0 PASS => valid AA0 reuse only;
15. exact predecessor materialisation => eligible speculative successor promotes without rebuild;
16. missing/unknown assurance classification => AA2/no-reuse conservative fallback;
17. partial/queued/unavailable required evidence => cannot satisfy set;
18. reference polling/reconciliation and event-driven path => identical logical future/intent decisions.

Zero tolerance remains: false authority allow, duplicate effective merge, accepted tree mismatch, parallel physical merge, lost mandatory completion receipt, provider-adapter write reachability.

## 6. Workflow and assurance stratification

Implementation may classify existing GitHub workflows only through explicit versioned configuration, never by inferred name. Initial repository bindings SHALL treat current repository/unit/parity surfaces as candidate AA0 only where their dependency scope is explicitly declared. FINAL/currentness/SIQ/lease checks remain AA2 unless an exact prospective-tree owner contract explicitly supports AA1 reuse.

No current required workflow may be removed, demoted or treated as optional by this programme.

## 7. Branch, CI, QA and integration discipline

- AA-WP0 uses its own plan branch/PR from lawful main.
- AA-WP1…AA-WP5 use one approved grouped branch from the post-WP0 lawful main.
- All changes require focused tests plus repository-wide suite, runner parity, pytest/unittest parity, current FINAL_HEAD profile, programme-state pointer preflight, SIQ READY and exact merge-readiness where applicable.
- Correctable defects are repaired in scope and tests rerun.
- Non-reserved PASS gates are delegated/auto-ratified, committed, pushed and squash-merged.
- No force-push/history rewrite.
- Implementation closeout must use the existing canonical DEVOBS/receipt path and may not create a new permanent writer.

## 8. Activation gate

`DSAI3V-AA-G-ACTIVATE` is OPERATOR_REQUIRED after AA-G5 PASS.

The consolidated activation packet MUST state:
- exact implementation/qualification commits and merge SHAs;
- exact active default substrate and controller identity;
- whether live activation reuses the existing controller capability or requires a new writer/service identity;
- exact proposed default-substrate delta;
- workflow/provider binding and RequiredAssuranceSet profile;
- all mandatory fixtures/tests/QA;
- reference/event reconciliation equivalence;
- DEVOBS shadow measurements where available;
- unresolved warnings/incidents;
- rollback to foreground-wait behavior;
- explicit confirmation that physical integration remains serialized and all programme-owned authority boundaries remain unchanged.

Until operator PASS, Async Assurance runtime status is `IMPLEMENTED_QUALIFIED_INACTIVE_OR_SHADOW`; current foreground-wait/live materialisation semantics remain authoritative.

## 9. Rollback

Before activation, disable/supersede async futures/intents/provider observation routing for new packets and preserve all generated evidence. After any future activation, forward-disable Async Assurance routing and return affected packets to the prior DSAI3V foreground-wait/currentness path. Never rewrite historical futures, signals, intents, receipts or Git history.

## 10. Terminal target

The implementation programme terminates at:

`ASYNC_ASSURANCE_IMPLEMENTED_QUALIFIED_INACTIVE_OR_SHADOW / DSAI3V-AA-G-ACTIVATE GATE_READY`

unless a separate explicit operator PASS activates the capability. This plan itself grants no live activation.
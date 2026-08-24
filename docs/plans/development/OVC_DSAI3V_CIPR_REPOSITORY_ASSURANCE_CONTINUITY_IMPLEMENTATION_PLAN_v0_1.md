# OVC DSAI3V + CIPR Repository Assurance Continuity

## Conformance Implementation Plan v0.1

- **Programme ID:** `OVC-DSAI3V-CIPR-REPOSITORY-ASSURANCE-CONTINUITY-AMENDMENT-0.1`
- **Plan ID:** `OVC-DSAI3V-CIPR-RAC-CONFORMANCE-IMPLEMENTATION-PLAN-0.1`
- **Repository:** `owenguobadia24s-collab/ovc-replay`
- **Implementation namespace:** `DSAI3V-RAC-WP*` / `DSAI3V-RAC-G*`
- **Operator mandate:** `OVC RUN OVC-DSAI3V-CIPR-REPOSITORY-ASSURANCE-CONTINUITY-AMENDMENT-0.1`
- **Planning baseline:** `main@15c7531c3635e96681dc87b906455969fe21b6f3`
- **Planning tree:** `2d799bf6454f50327c566c0c51fe7654d587ae85`
- **Status:** G0 PASS RECORDED / BOUNDED IMPLEMENTATION AND SHADOW QUALIFICATION AUTHORISED
- **Default terminal:** `IMPLEMENTED_SHADOW_QUALIFIED / LIVE_BLOCKING_PATH_UNCHANGED`
- **First reserved transition:** `DSAI3V-RAC-G-DELTA-ASSURANCE-PILOT`

## 0. Execution decision

Conform the operator-approved architecture amendment as an additive DSAI/VIT assurance subsystem coordinated with CIPR. Do not replace VIT, SIQ, GRT, Shared Systems, the canonical pytest route or the active GitHub ruleset.

The default programme implements the canonical assurance objects, deterministic reference engine, synthetic/adversarial corpus, coarse source-bound bootstrap evidence and non-authoritative shadow tooling. It stops before any required-check substitution or live blocking-path cutover.

## 1. Source precedence

1. Repository `main` and accepted operator decisions control present state and authority.
2. `OVC_DSAI3V_CIPR_REPOSITORY_ASSURANCE_CONTINUITY_AMENDMENT_v0_1.md` controls this amendment's semantics.
3. Active DSAI/VIT late-binding, assurance-decoupling and physical-main-exclusivity records remain controlling.
4. GRT owns repository-law proof and reference/incremental conformance semantics.
5. CIPR current records own its shard/reference execution evidence and its separate cutover gate.
6. Shared Systems may be consumed only under exact current service bindings.
7. Missing authority, dependency coverage or evidence fails closed and is not inferred from this plan.

## 2. Current court-record reconciliation

At planning time:

- DSAI3V VIT is complete and active as the default execution substrate.
- AA0 PIP-bound reuse already prevents full rerun for lawful placement-only main movement.
- a new PIP still ordinarily executes the complete canonical repository assurance surface;
- CIPR post-PYT deterministic pytest shard shadow has qualified and is parked at operator-required `CIPR-G5-POST-PYT-CONSOLIDATED-CUTOVER`;
- required-check substitution and runner cutover are not active;
- physical main remains one-writer VIT -> SIQ;
- GRT exact-final proof remains mandatory.

This plan reuses the qualified shard work as reference-executor evidence only. It does not consume or supersede the CIPR cutover decision.

## 3. Work packets

### DSAI3V-RAC-WP0 — mandate and authority materialisation

Outputs:

- amendment contract;
- this plan;
- exact operator-instruction record;
- authority manifest;
- dependency frontier;
- programme state and current pointer.

Gate `DSAI3V-RAC-G0` is satisfied by the exact operator RUN command. Authority is limited to implementation, synthetic/adversarial execution, historical replay and non-authoritative shadow qualification.

### DSAI3V-RAC-WP1 — canonical objects and deterministic identity

Implement:

- `AssuranceClaimSpec`;
- `AssuranceDependencyGraph`;
- `RepositoryAssuranceGeneration`;
- `MutationImpactManifest`;
- `DeltaAssurancePlan`;
- `CandidateAssuranceCertificate`;
- `ReferenceReconciliationReceipt`.

Acceptance:

- canonical IDs are order-independent where semantics are set-valued;
- malformed IDs and overlapping claim states fail closed;
- duplicate claim IDs fail closed;
- no object contains physical-main authority;
- all code uses existing canonical identity primitives.

### DSAI3V-RAC-WP2 — impact closure and candidate certification

Implement deterministic claim classification:

- unchanged passed claim -> `INHERIT_VALID`;
- declared dependency intersection -> `RERUN_REQUIRED`;
- bounded large closure -> `WIDE_RERUN_REQUIRED`;
- global/unbounded/reference-only or unresolved surface -> `FULL_REFERENCE_REQUIRED`;
- inherited not-evaluable/quarantined state remains blocking.

Acceptance:

- unrelated main movement returns `PLACEMENT_ONLY`;
- dependency intersection renews only affected claims;
- global harness/environment/workflow movement escalates;
- unclassified mutation cannot inherit assurance;
- candidate certificate cannot pass a failing, missing, quarantined or not-evaluable obligation.

### DSAI3V-RAC-WP3 — reference reconciliation and incident semantics

Implement reference comparison and `ASSURANCE_MODEL_DIVERGENCE` receipts.

Acceptance:

- missing reference claims are divergence;
- failing reference claims are divergence;
- deterministic clean replay reproduces the same graph, plan, certificate and receipt IDs;
- no divergence can be converted to a scoped PASS in the same generation.

### CIPR-RAC-WP1 — executor-role constitution

Materialise policy for:

- `DELTA_EXECUTOR`;
- `WIDE_EXECUTOR`;
- `REFERENCE_EXECUTOR`.

No workflow or required-check change is made in the initial packet. Existing canonical pytest and qualified shard surfaces remain unchanged. CIPR executes obligations supplied by DSAI; it does not define semantic omission.

### DSAI3V-RAC-WP4 — adversarial and synthetic truth worlds

Required cases:

- disjoint PIPs;
- overlapping dependency owner;
- unclassified mutation;
- global harness change;
- unbounded claim;
- stale/malformed generation;
- duplicate claim;
- missing/failing reference result;
- cache/index loss model;
- three-lane mixed impact;
- placement-only main movement;
- GRT/currentness/global surface escalation.

Gate `DSAI3V-RAC-G1-MECHANICAL` is AUTO_RATIFIABLE after WP1-WP4 and exact QA pass.

### DSAI3V-RAC-WP5 — bootstrap and shadow-readiness evidence

Bind a coarse, explicitly incomplete shadow-only claim-family registry to the then-current physical tree and current CIPR/DSAI/GRT evidence. The bootstrap MUST state that it is not sufficient for blocking-path substitution.

Produce:

- bootstrap source manifest;
- synthetic shadow execution fixture;
- deterministic output receipt;
- completeness state `COARSE_CLAIM_FAMILIES_ONLY`;
- explicit `LIVE_BLOCKING_PATH_UNCHANGED` result.

Gate `DSAI3V-RAC-G2-REFERENCE-EQUIVALENCE` is AUTO_RATIFIABLE after exact reference/delta truth-world agreement.

### DSAI3V-RAC-WP6 — measured multi-lane live shadow

Future non-authoritative packet. It consumes real eligible PIP metadata read-only, compares predicted delta/wide/reference obligation sets with canonical reference results, and records false-positive/false-negative/latency/invalidation-radius evidence.

No CI substitution, merge permission or required-check change is allowed.

Gate `DSAI3V-RAC-G3-SHADOW-QUALIFICATION` is AUTO_RATIFIABLE only after the frozen evidence budget is satisfied with zero unexplained semantic mismatch.

## 4. Reserved gates

### DSAI3V-RAC-G-DELTA-ASSURANCE-PILOT

Operator decision required before any live packet class may use a CandidateAssuranceCertificate instead of the complete canonical blocking suite.

The gate packet must include:

- exact claim coverage and completeness;
- reference/delta comparison corpus;
- false-negative evidence;
- dependency-graph maintenance burden;
- latency distribution;
- fallback and incident drills;
- GRT/SIQ/VIT compatibility;
- required-check/ruleset proposal, if any;
- rollback.

### DSAI3V-RAC-G-DELTA-ASSURANCE-GENERAL

Operator decision required before normal eligible permanent packets may use delta assurance generally.

## 5. Repository placement

- contract: `contracts/development/v0_5/`
- schemas: `schemas/development/skills/`
- policy/claim registry: `registries/development/skills/`
- implementation state: `registries/implementation/dsai3v_cipr_rac/`
- runtime: `src/ovc/development/skills/`
- tests: `tests/development/`
- fixtures: `fixtures/development/repository_assurance_continuity/`
- compact programme evidence: `docs/releases/development-skills-architecture-v0-3-vit/repository-assurance-continuity/`

Routine generations/indexes remain external or rebuildable; no routine Git churn.

## 6. QA and reference equivalence

Initial required QA:

- targeted RAC tests;
- existing DSAI/VIT assurance-decoupling tests;
- canonical repository pytest;
- pytest/unittest parity;
- runner parity;
- profile assurance;
- VIT routing and SIQ READY;
- GRT exact-final assurance;
- `OVC merge readiness`.

The initial implementation may merge only as inactive/shadow machinery. It must not alter `.github/workflows/tests.yml`, `.github/workflows/ovc-tiered-tests.yml`, the required ruleset, the default substrate's required-assurance list or the current CIPR cutover state.

## 7. Failure and rollback

Any identity failure, dependency ambiguity, stale graph/policy, uncovered changed surface, reference disagreement, GRT mismatch, SIQ failure or tree mismatch fails closed.

Rollback forward-disables the RAC policy and removes it from future shadow selection while preserving all artifacts and history. Existing canonical CI remains the safe fallback throughout the default programme.

## 8. Definition of default completion

The default programme is complete only when:

- canonical objects and policy are implemented;
- deterministic/adversarial tests pass;
- reference reconciliation is fail-closed;
- source-bound coarse bootstrap evidence exists;
- live blocking path is explicitly unchanged;
- no required-check/ruleset/runtime cutover occurred;
- the programme is parked at `DSAI3V-RAC-G-DELTA-ASSURANCE-PILOT` after measured shadow qualification, or at the first genuine unresolved blocker.
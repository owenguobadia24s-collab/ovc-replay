# OVC Parallel Development / Main-Head Churn Remediation

Implementation Plan v0.1

## Document control

- **programme_id:** `OVC-PARALLEL-DEVELOPMENT-HEAD-CHURN-v0.1`
- **plan_id:** `OVC-PDC-IMPLEMENTATION-PLAN-0.1`
- **repository:** `owenguobadia24s-collab/ovc-replay`
- **baseline_main:** `554710ca7b94760d84362d8ae5ad568e27478eec`
- **prepared:** `2026-08-09`
- **operator instruction:** `yes lets implement OVC Parallel Development / Main-Head Churn Remediation plan`
- **status:** `RATIFIED_FOR_BOUNDED_IMPLEMENTATION`
- **authority effect:** `NONE` outside development orchestration and assurance.

## 0. Decision

Implement a bounded development-orchestration programme that permits concurrent isolated packet construction while making integration to `main` a single serialized lane. Main movement is classified by dependency impact rather than commit count alone. Expensive scientific/replay evidence remains reusable when its immutable input identities did not change; exact integration assurance remains mandatory before merge.

This programme extends Development Acceleration v0.2. It does not weaken the DA2 requirement for one canonical complete repository suite on the exact tested candidate/merge state and it does not allow stale branches to merge without reconciliation.

## 1. Problem

Several OVC programmes can legitimately build at the same time. During long packets, `main` may advance repeatedly because unrelated packets, receipts, gates, console changes or research programmes merge. Treating every `main` advance as full semantic invalidation causes repeated preflight, replay reasoning, evidence reconstruction and CI work. Treating all movement as harmless creates the opposite risk: stale contracts, authority records or source identities can be consumed after they changed.

The remediation therefore separates **parallel build** from **serialized integration** and classifies intervening `main` changes.

## 2. Head-movement classes

### `IRRELEVANT`

Intervening `main` changes do not intersect the packet dependency footprint, protected semantic/authority identities, candidate-owned paths, or shared integration infrastructure.

Required response: retain existing scientific/replay evidence; no semantic re-preflight solely because the commit count changed. Exact integration assurance still applies.

### `INTEGRATION_RELEVANT`

Intervening changes affect shared tooling, workflows, test infrastructure, packaging/dependency files, or candidate-owned paths but do not alter a declared consumed semantic/authority identity.

Required response: reconcile with current `main`; rerun impacted tests and required final integration assurance. Do not repeat expensive scientific computation whose frozen inputs remain unchanged.

### `SEMANTIC_AUTHORITY_RELEVANT`

Intervening changes alter any declared consumed contract, schema, authority record, source/release identity, selector/pack identity, governing design source, programme prerequisite, or explicitly protected dependency path.

Required response: full semantic re-preflight; re-resolve bindings and authority; regenerate dependent evidence when necessary; BLOCK or SUPERSEDE if the packet premise no longer holds.

### `UNRESOLVED_REQUIRES_FOOTPRINT`

`main` moved but no adequate packet dependency footprint exists. This is fail-closed and may not be downgraded by intuition.

## 3. Dependency footprint contract

Every new long-running or concurrently developed permanent packet SHOULD materialize a compact dependency footprint before expensive work begins. A footprint contains:

- programme / packet / plan identity;
- `baseline_main_sha`;
- consumed exact paths or glob prefixes;
- consumed identity-bearing files and expected hashes where available;
- shared integration paths;
- semantic/authority protected paths;
- immutable external artifact identities that permit replay reuse;
- explicitly declared exclusions.

The classifier evaluates the exact set of paths changed on `main` between the packet baseline and current integration baseline. Classification evidence is deterministic and machine-readable.

## 4. Integration lane

There is one logical integration lane for `main`.

- Build/test work on isolated branches may remain concurrent.
- The `OVC merge readiness` job is serialized repository-wide with `cancel-in-progress: false`.
- The job snapshots the current `main` SHA before readiness evaluation and verifies that `main` is unchanged before PASS.
- If `main` changes during readiness, the job fails closed with a base-movement reason and a fresh readiness run is required.
- A readiness PASS does not itself grant merge authority; existing OVC gate and authority rules continue to govern merge.
- Immediately before an eligible squash merge, the operator/automation must still pin PR head and verify the current lawful `main` base.

This lane serializes final integration evaluation, not development work.

## 5. Evidence reuse rule

A changed Git commit is not sufficient evidence that a scientific result is stale. Reuse is lawful only when the exact immutable scientific/input identities bound by the packet remain unchanged and the head-movement classifier does not return `SEMANTIC_AUTHORITY_RELEVANT`.

No classifier result may bypass:

- a separately reserved real-source or Validation gate;
- a selector/pack activation gate;
- semantic/family/model/theory promotion authority;
- publication or exposure authority;
- a test explicitly required by the owning plan.

## 6. Work packets

### PDC-WP0 — programme bootstrap and policy freeze

Outputs:

- this implementation plan;
- machine-readable programme state;
- operator ratification record derived from the explicit instruction to implement this programme.

Gate `PDC-G0`: operator instruction already supplied; authority delta is development orchestration only.

### PDC-WP1 — deterministic head-movement classifier

Outputs:

- dependency-footprint schema;
- head-movement policy registry;
- Python classification library and CLI;
- deterministic unit/adversarial tests.

Acceptance:

- identical input produces identical classification/receipt;
- missing footprint fails closed when movement exists;
- unrelated paths classify `IRRELEVANT`;
- shared/tooling paths classify `INTEGRATION_RELEVANT`;
- consumed/protected semantic paths classify `SEMANTIC_AUTHORITY_RELEVANT`;
- highest-severity match wins;
- replay-reuse recommendation is never emitted for semantic/authority movement.

Gate `PDC-G1`: AUTO-RATIFIABLE if tests and QA pass.

### PDC-WP2 — serialized merge-readiness lane

Outputs:

- DA2-compatible update to `.github/workflows/ovc-tiered-tests.yml`;
- repository-wide job-level concurrency for `OVC merge readiness`;
- current-main snapshot and end-of-job stability check;
- regression tests that preserve the two authorised PR workflows, canonical `tests` suite and no duplicate complete suite.

Acceptance:

- no additional pull-request workflow is introduced;
- existing per-PR cancellation remains;
- merge-readiness final evaluation is serialized globally;
- main movement during readiness fails closed;
- no scientific/authority semantics are changed.

Gate `PDC-G2`: AUTO-RATIFIABLE if exact-head repository and OVC tiered assurance pass.

## 7. Branch and merge discipline

The three packets are an approved grouped infrastructure packet set because they implement one inseparable development-orchestration control and have authority effect `NONE` outside development workflow assurance.

Branch: `build/parallel-development-head-churn-remediation-v0-1` from the pinned baseline.

Before merge:

1. resolve latest lawful `main`;
2. classify base movement since `554710ca7b94760d84362d8ae5ad568e27478eec`;
3. reconcile if required;
4. run exact-head repository and OVC tiered/profile assurance;
5. confirm zero blocking review threads;
6. squash-merge only if all acceptance conditions pass.

No force-push or history rewrite is permitted.

## 8. Rollback

Rollback is non-destructive: revert/supersede the classifier/policy/workflow changes while preserving this plan, decisions, CI evidence and historical receipts. Restoring the prior DA2 workflow means removing only the job-level integration-lane/stability additions; the existing DA2 orchestration contract remains intact.

## 9. Final state

Target state: `COMPLETED / PARALLEL_BUILD_SERIALIZED_INTEGRATION_ACTIVE`.

No selector, market, scientific, family, semantic, Validation, publication, probability, risk, exposure, execution or agent-write authority is created.
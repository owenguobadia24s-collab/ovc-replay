# OVC Parallel Development / Main-Head Churn Contract v0.1

## Identity

- programme: `OVC-PARALLEL-DEVELOPMENT-HEAD-CHURN-v0.1`
- plan: `OVC-PDC-IMPLEMENTATION-PLAN-0.1`
- baseline main: `554710ca7b94760d84362d8ae5ad568e27478eec`
- parent orchestration contract: `OVC Development Acceleration v0.2 PR Orchestration Contract v0.1`

## Constitutional rule

OVC may develop multiple bounded packets concurrently, but permanent integration into `main` is serialized. A movement of `main` invalidates only the work whose declared dependency or integration surface is affected. Commit-count growth by itself is not a semantic invalidator.

## Required packet evidence

A long-running or concurrent packet that intends to reuse expensive evidence after `main` moves must possess a machine-readable dependency footprint. Without one, movement is `UNRESOLVED_REQUIRES_FOOTPRINT` and scientific evidence reuse is denied until resolved.

A dependency footprint must distinguish:

- consumed dependencies / exact identity-bearing paths;
- semantic or authority paths;
- shared integration paths;
- candidate-owned paths;
- immutable external evidence identities.

## Main-head movement classes

`IRRELEVANT`: no declared dependency, semantic/authority, candidate-owned or shared integration path changed.

`INTEGRATION_RELEVANT`: shared tooling, workflow, test, packaging or candidate-owned integration surface changed, but no declared consumed semantic/authority identity changed.

`SEMANTIC_AUTHORITY_RELEVANT`: a consumed contract, schema, authority, selector/pack/source/release identity, governing source or prerequisite changed.

`UNRESOLVED_REQUIRES_FOOTPRINT`: `main` moved and the packet lacks sufficient dependency evidence.

Highest severity wins.

## Evidence reuse

`IRRELEVANT` and `INTEGRATION_RELEVANT` may retain expensive scientific/replay evidence only when every bound immutable input identity remains unchanged. `SEMANTIC_AUTHORITY_RELEVANT` and `UNRESOLVED_REQUIRES_FOOTPRINT` may not reuse such evidence until their required re-preflight is satisfied.

This reuse rule never waives owner-plan tests, exact final integration assurance, real-source authority, Validation protections, promotion gates, publication controls or exposure controls.

## Serialized integration lane

`OVC merge readiness` is the sole final readiness evaluator and uses one repository-wide non-cancelling concurrency lane. It snapshots the target base branch before readiness and verifies the base did not move before PASS. A base change before or during readiness fails closed and requires a fresh readiness run.

The existing per-PR concurrency cancellation remains active for ordinary CI. The existing canonical complete repository suite remains exactly one `tests` execution per tested PR state. No new pull-request workflow is admitted.

## Merge boundary

A readiness PASS is evidence, not merge authority. Existing OVC packet/gate authority still determines whether a squash merge is eligible. The PR head must be pinned and current `main` rechecked immediately before merge.

## Rollback

Rollback is append-only/non-destructive. The classifier, policy and integration-lane additions may be reverted or superseded without rewriting historical decisions or scientific evidence. The Development Acceleration v0.2 parent contract remains preserved.

# OVC DSAI/VIT Late-Binding Integration Contract v0.2

Status: OPERATOR-RATIFIED AMENDMENT / IMPLEMENTATION CANDIDATE  
Programme: `OVC-DSAI-VIT-v0.3`  
Amendment packet: `DSAI3V-LB-WP1`  
Authority delta: development integration mechanics only; scientific/market authority `NONE`.

## Purpose

Replace early physical-main placement and train-predecessor blocking with a late-bound, work-conserving integration model while preserving one physical writer, exact prospective-tree proof, GRT conformance, immutable PIP identity, append-only evidence, and physical `main` as the sole operational court record.

## Constitutional rules

### LB-A — no early physical-main binding

A `PacketIntegrationPayload` (PIP) and its base-independent assurance MUST NOT acquire a decision-bearing physical-main predecessor, VIT train ordinal, or physical placement before the candidate owns the final integration lease.

A permanent PR MAY carry historical v1 placement provenance during migration, but v1 predecessor/tree/ordinal fields are non-authoritative for qualification and MUST NOT create a wait edge.

### LB-B — no absolute queue position

The integration scheduler operates over a dynamically evaluated runnable frontier. Arrival order, PR number, prior train ordinal, and prior VIT placement MAY be fairness tie-breakers only among currently runnable candidates. They MUST NOT create blocking authority.

A candidate may be blocked only by an explicit owner/dependency prerequisite, an actual content/conflict relation, an authority/security boundary, failed required assurance, or the momentary one-writer physical-main transaction.

If candidate B is not runnable and independent candidate C is runnable, B MUST NOT prevent C from being selected merely because B arrived earlier or had a lower ordinal/PR number.

### LB-C — VIT owns late physical placement

After a qualified payload is selected and enters the one-writer integration lane, VIT SHALL:

1. resolve physical `main` at that moment;
2. compose the stable payload/candidate onto that exact physical base;
3. create an ephemeral `LateBindingPlacement`;
4. run only genuinely base-sensitive exact-final assurance on the prospective tree;
5. require exact GRT/tree equality for the materialised result;
6. discard the placement after materialisation or invalidation.

The placement identity is transient integration state, not payload identity. A placement becoming stale MUST NOT by itself create a new PIP, development commit, branch, or PR.

### LB-D — impact-scoped invalidation

Physical-main movement MUST be classified by actual impact:

- `PLACEMENT_ONLY`: unchanged PIP, authority and dependency frontier; base-independent assurance remains valid.
- `ASSURANCE_RENEWAL_REQUIRED`: a changed main surface intersects a declared assurance dependency.
- `AUTHORITY_REVIEW_REQUIRED`: controlling authority changed.
- `PAYLOAD_INVALIDATED`: the PIP or an identity-bearing dependency frontier changed.

Unrelated main movement MUST NOT trigger full assurance replay or replacement-candidate generation.

### LB-E — one physical writer remains

Parallel physical writes remain prohibited. The only serialized portion is the bounded final physical-main transaction and the exact-final assurance that must remain stable against that transaction's acquired base.

The global physical-main lane MUST NOT be used to serialize base-independent qualification or to wait on unrelated PRs.

### LB-F — payload identity is stable

PIP identity remains content-addressed from logical changes, authority manifest, dependency frontier, and completion transition. Branch, PR, worker, physical base, train position, placement, and runtime timestamps are provenance or transient state only.

### LB-G — migration and history

Historical v1 VIT generations/placements remain immutable and replayable. This amendment supersedes their forward use as blocking live-integration order. No historical record is rewritten.

## Required objects

- `PacketIntegrationPayload` — durable logical mutation identity.
- `BaseIndependentAssuranceGeneration` — PIP-bound qualification evidence with no physical-main binding.
- `QualifiedPayloadCandidate` — candidate state used by the runnable-frontier evaluator.
- `RunnableFrontierDecision` — dynamic runnable/blocked projection; not scientific or repository authority.
- `LateBindingPlacement` — ephemeral physical-main placement created only inside the final integration lane.
- existing `IntegrationAdmissionReceipt`, `PhysicalMaterialisationReceipt`, `PacketCompletionReceipt`, and GRT exact-tree proof — preserved.

## Fail-closed behavior

Content conflict, authority conflict, missing true dependency, failed assurance, security denial, GRT failure, tree mismatch, or physical-main movement during exact-final assurance fails closed.

Physical-main movement before or during a placement invalidates that placement only unless a separately proven impact classification requires wider renewal.

## Explicit non-grants

This contract grants no selector/model/family/candidate/theory/scientific promotion, no `ACTIVE_DISCOVERY` / `ACTIVE_DEVELOPMENT` / `ACTIVE_VALIDATION` transition, no Validation, publication, probability, risk, exposure, trading, execution, force-push, history rewrite, destructive action, parallel physical merge, or general agent-write authority.

## Rollback

Rollback is forward-only: disable late-binding admission, restore the prior qualified VIT/SIQ admission route by a versioned superseding change, preserve all v1/v2 PIPs, placements, assurance generations, receipts and operator decisions, and never rewrite Git history.

# OVC VIT Assurance Decoupling + Physical-Main Exclusivity Contract v0.1

Status: corrective conformance contract under existing VIT general authority and active Async Assurance authority  
Authority effect: `NONE_SAFETY_CONFORMANCE_CORRECTION`

## 1. Purpose

This contract removes physical-main head churn from the identity and expensive-assurance path of already-authorised permanent development packets. It does not create a new programme authority, writer identity, packet class, merge method, scientific authority, publication authority, or parallel physical merge path.

The governing topology is:

`parallel packet construction -> PIP -> VIT train/generation -> qualified assurance -> VIT controller -> SIQ -> physical main`.

Physical `main` is a materialised output of the VIT train. It is not the scheduler or identity source for competing development packets.

## 2. Assurance classes

### AA0 — PIP-bound background assurance

Expensive repository, unittest-parity and runner-parity assurance is bound to the immutable `PacketIntegrationPayload` plus an assurance-harness fingerprint.

An exact VIT-generation cache hit may be reused directly. Cross-generation reuse is permitted only when a canonical `VIT-AA0-Reuse-B64` authorization proves that the PIP, dependency frontier and authority manifest are unchanged and the intervening head movement is classified by the existing deterministic head-movement contract as `IRRELEVANT` or `INTEGRATION_RELEVANT` with bound-evidence reuse permitted.

Payload, dependency-frontier or authority change, semantic-authority movement, unresolved movement, invalid authorization, or changed assurance harness fails closed to fresh AA0 or semantic repreflight.

### AA1 — prospective-tree assurance

Short profile/orchestration assurance is bound to the current `VirtualIntegrationGeneration` and its result tree. Placement refresh renews AA1; it does not invalidate lawful AA0 reuse.

### AA2 — materialisation-edge assurance

SIQ/PDC exact-final assurance remains bound to the current physical predecessor and current VIT generation. AA2 is never reusable across a physical-predecessor change.

### AA3 — post-write equivalence

After materialisation, physical tree equality with the qualified VIT result tree remains mandatory and non-reusable.

## 3. Placement-only main movement

When the packet PIP, dependency frontier and authority manifest remain unchanged, unrelated lawful physical-main movement is placement context only.

The lawful response is:

`same PIP -> recompute VIT generation/placement -> reuse AA0 only when explicitly proven -> renew AA1/AA2 -> materialise through SIQ -> prove AA3`.

A placement-only advance must not create a new logical payload merely to obtain a fresh base and must not rerun AA0 when an exact-generation cache or valid placement-only reuse authorization is available.

## 4. Competing development lines

All eligible permanent packets fold into VIT before physical integration. `VirtualIntegrationLedger` and the VIT controller own prospective ordering. Commutative work may build ahead; order-sensitive, shared-owner or conflicting work remains serialized in the VIT train.

The invariant is:

**parallelism above VIT; serialization below VIT.**

Branches remain non-authoritative construction transports. A branch, pull request, ORCH selection, QA result or green provider check does not independently own a physical-main write.

## 5. Physical-main exclusivity

The only lawful logical main writer is `DSAI_VIT_PHYSICAL_CONTROLLER`, and its only physical gateway is `DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY`.

Every permanent PR must pass the canonical VIT routing preflight. Every physical merge must pass the GitHub-required `OVC merge readiness` check. The active repository ruleset must remain fail-closed with:

- pull request required;
- squash as the only merge method;
- non-fast-forward updates prohibited;
- deletion prohibited;
- `OVC merge readiness` required from the bound GitHub Actions provider;
- native strict branch-up-to-date enforcement disabled because current-main composition and exact-final assurance are performed inside the serialized VIT/SIQ integration lease;
- zero bypass actors.

The required CI preflight re-reads the live GitHub ruleset on every permanent PR. A missing, inactive, ambiguous or bypassable ruleset blocks assurance before the packet can become a physical-main candidate.

Native required-check strictness MUST NOT be used as an additional physical-placement mechanism. For a late-binding candidate, unrelated movement of `main` is handled by the existing `OVC merge readiness` lease: resolve current `main`, construct the ephemeral prospective tree, run exact-final SIQ/PDC assurance on that exact tree, and bind the IntegrationAdmissionReceipt. The stable payload branch is not required to absorb unrelated `main` commits merely to satisfy repository UI currentness.

This contract does not add a workflow merge credential. Repository materialisation continues through the existing authorized external merge path after VIT/SIQ readiness.

## 6. Main-head churn semantics

A lawful VIT materialisation may advance physical main. Such movement must update descendant placement context but must not be treated as a reason to discard unchanged packet payloads.

A physical-main mutation that cannot be attributed to a pull request satisfying VIT lineage plus required `OVC merge readiness` is an integration-exclusivity incident, not normal development churn.

## 7. Observability

DEVOBS must distinguish:

- fresh AA0 execution;
- exact-generation AA0 reuse;
- placement-only PIP AA0 reuse;
- AA1 renewal;
- AA2 renewal;
- payload rebuild.

The target steady state for unrelated competing lines is `payload_rebuild_count=0` and no repeated expensive AA0 run caused only by a physical-main advance.

## 8. Authority boundary

No selector/model/family/candidate/theory promotion, ACTIVE_DISCOVERY/DEVELOPMENT/VALIDATION grant, canonical/R2 publication, probability/risk/exposure/execution authority, GRT2-G3 activation, force-push, history rewrite, parallel physical merge, or new writer identity is granted.

Operator-required packets remain represented in VIT and park at their existing programme-owned authority boundary.

## 9. Rollback

Rollback is forward-only. Restore native strict branch-up-to-date enforcement only together with a versioned superseding integration design that does not reintroduce payload/head churn; otherwise disable cross-generation AA0 reuse and the additional live ruleset preflight while preserving active VIT/SIQ authority, universal routing enforcement, required `OVC merge readiness`, zero bypass, all PIPs/generations/placements, assurance evidence, DEVOBS receipts and Git history.

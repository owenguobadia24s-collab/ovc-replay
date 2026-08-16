# OVC VIT Universal Routing Conformance Contract v0.1

Status: corrective conformance contract under existing `DSAI3V-VIT-GENERAL-AUTHORITY-v0.1`  
Authority effect: `NONE_SAFETY_CONFORMANCE_CORRECTION`

## 1. Purpose

This contract closes the gap between active VIT authority and universal mechanical adoption. It does not activate VIT, create a new writer, broaden packet eligibility, alter programme-owned authority, or permit parallel physical merge.

## 2. Binding route

For every already-authorised permanent development packet, including packets that later park at an operator-required boundary, the lawful route is:

`packet resolution -> bounded construction transport -> PacketIntegrationPayload freeze -> exact VIT generation -> LedgerPlacement -> permanent PR/integration-candidate admission -> assurance -> DSAI_VIT_PHYSICAL_CONTROLLER -> DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY -> exact physical/VIT tree equality -> completion/DEVOBS receipts`.

A Git branch may exist as a non-authoritative construction transport. Branch/PR metadata is provenance only; it is never packet identity, authority, or a competing scheduler.

## 3. PIP and permanent-candidate invariant

Before a branch becomes a permanent PR/integration candidate, its identity-bearing mutation MUST be frozen as canonical `PacketIntegrationPayload`; the reference apply of that PIP to the exact PR base tree MUST reproduce the exact PR head tree; and the PR MUST carry the corresponding canonical VIT generation and `LedgerPlacement` identities.

The full lineage MUST validate against `ovc-vit-routing-lineage/v1` and preserve the exact `PacketIntegrationPayload.payload_id`, `VirtualIntegrationGeneration.generation_id`, and `LedgerPlacement.placement_id` semantics already defined by DSAI3V.

The lineage envelope MUST NOT be committed inside the tree whose identity it binds because that would create a self-referential result-tree identity. Instead the canonical compact lineage JSON is carried as `VIT-Lineage-B64` in the PR court-record metadata, is revalidated by required assurance against the exact checked-out base/head trees, and is persisted again by the controller/completion receipt chain. `tools/ci/build_vit_pr_lineage.py` is the reference producer.

## 4. SIQ invariant

SIQ is only the physical one-head materialisation gateway. A `QueueCandidate` without the fully validated PIP, VIT generation, VIT placement, matching identifiers and lineage provenance MUST fail closed and MUST NOT become `READY` or acquire the final-integration lease.

A finite PR-preflight exception never grants SIQ bypass. SIQ accepts only normal `VIT_MANDATORY` lineage. No queue state, lease, QA result, branch ancestry, pull request or workflow result can substitute for VIT lineage.

## 5. Main movement and rebuild classification

Physical-main movement is placement context, not payload identity.

When PIP identity, dependency frontier and authority are unchanged, an unrelated lawful main advance MUST be classified `PLACEMENT_RECOMPUTE_ONLY` with `payload_rebuild_required=false`. Affected assurance may be renewed and a new placement/materialisation projection may be produced on the same logical packet/PR lineage.

`PAYLOAD_REBUILD_REQUIRED` is lawful only when an identity-bearing packet change, dependency-frontier change, or real packet-local defect changes the payload. Prior failed/replaced evidence remains preserved.

Creating a fresh logical payload or replacement pull request solely because physical main moved is `LEGACY_FRESH_MAIN_RECONCILE` and is prohibited.

## 6. Operator boundaries

`OPERATOR_REQUIRED` does not create a VIT exception. The packet is represented in VIT and parks at its programme-owned authority boundary. No operator-reserved authority is crossed by this contract.

## 7. External branch and pull-request surfaces

Repository code cannot prevent an external tool from creating a Git ref, so such a ref remains non-authoritative construction transport. A pull request to `main` cannot become a lawful permanent integration candidate unless the required routing preflight proves either:

1. a valid inline `VIT-Lineage-B64` envelope whose PIP reference-apply exactly reproduces the PR head from the PR base and whose generation/placement trees equal those exact Git trees; or
2. one exact finite `REGISTERED_EXCEPTION` in `VIT_ROUTING_COVERAGE_REGISTER_v0_1.json`.

An exception never grants SIQ, merge, programme, scientific or other reserved authority.

## 8. Orchestration and assisted Git surfaces

ORCH-3/4/5 may select or schedule already-authorised work, but selection is not execution. Automatic ORCH output must identify DSAI3V VIT as the required execution substrate and must not create a direct physical-main candidate.

Dry-run Git planning and assisted branch-push capabilities are also non-authoritative. Any surface that could make a remote branch a permanent candidate must preserve the VIT-before-PR invariant; the permanent PR preflight and SIQ checks remain mandatory even if an earlier construction tool did not itself materialise VIT lineage.

## 9. Assurance and observability

The universal routing correction must preserve all existing GRT, SIQ, exact-final, review, QA and DEVOBS obligations. DEVOBS must continue distinguishing placement recomputation/assurance renewal from payload rebuild. Synthetic/adversarial stale-main assurance must demonstrate zero payload rebuilds for unrelated main movement.

## 10. Forbidden effects

This contract does not grant new packet classes, new programme authority, new scientific authority, selector/model/family/candidate/theory promotion, ACTIVE_DISCOVERY/DEVELOPMENT/VALIDATION, publication, probability/risk/exposure/execution authority, force-push, history rewrite or parallel physical merge.

## 11. Rollback

Rollback is forward-only: disable/supersede this stricter routing-conformance layer while preserving active VIT/SIQ authority, audit evidence, failed lineage attempts, prior PIPs, placement generations and Git history.

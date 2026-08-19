# DSAI3V Late-Binding Post-Merge Recovery Correction v0.1

Packet: `DSAI3V-LB-CORR1-POSTMERGE-RECOVERY`  
Programme: `OVC-DSAI-VIT-v0.3`  
Parent amendment: `DSAI3V-LB-WP1` / DSAI v0.3 VIT Late-Binding Integration Amendment v0.1 — RATIFIED  
Authority delta: `NONE`

## Triggering evidence

The first physical merge under the late-binding route, PR #1227 / merge `b22ea057ddef98acc2e43dfff689b7fa56934385`, passed VIT routing, repository assurance, parity, FINAL_HEAD, SIQ READY and exact-final `OVC merge readiness`. The post-merge completion workflow then failed on the existing self-hosted Windows runner with:

`OVC_VIT_POST_MERGE_COMPLETION_FAILED: expected one pre-write transaction freeze for PR #1227, found 0`

The failure is an observability/recovery integration defect. The physical merge itself remains exactly tree-qualified.

## Root cause

The pre-existing completion extractor searched only `tests / VIT routing preflight` for `OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=`. The ratified late-binding redesign deliberately removed physical placement from that stage and emits `OVC_VIT_PREWRITE_FREEZE_DEFERRED=LATE_BINDING_NO_PHYSICAL_PLACEMENT` instead. The decision-bearing physical base and placement now first exist inside the serialized `OVC merge readiness` lane. Therefore the old extractor was asking the wrong lifecycle stage for an object that late-binding correctly cannot create there.

## Corrective rule

For payload-only late-binding lineage, the canonical post-merge recovery input is the exact pre-write evidence emitted by the successful serialized `OVC merge readiness` job:

- `OVC_VIT_LATE_BINDING_PLACEMENT_ACQUIRED=`;
- `OVC_INTEGRATION_ADMISSION_RECEIPT=`;
- the successful exact-final merge-readiness job/run identity.

The recovery tool deterministically reconstructs the `PhysicalMaterialisationTransaction` from those already-observed pre-write identities, revalidates PIP, placement, authority frontier, dependency frontier, candidate head, predecessor commit/tree, result tree and exact-final assurance binding, and then proves the physical post-write parent/tree before persisting any receipt. It does not infer a new placement from post-write main.

Historical placement-bearing lineage retains the direct VIT-routing freeze route.

## Bounded historical recovery

`VIT_POST_MERGE_RECOVERY_REQUESTS_v0_1.json` contains the exact first late-binding merge SHA `b22ea057ddef98acc2e43dfff689b7fa56934385`. The corrected self-hosted push workflow processes its current merge and this bounded recovery request. A previously completed proof is skipped idempotently. No physical write is replayed.

## Acceptance conditions

The correction passes only if:

1. unit tests prove a valid payload-only lineage can reconstruct exactly one PMT from successful merge-readiness placement/admission evidence;
2. missing or ambiguous exact-final markers fail closed;
3. the workflow uses the corrected extractor and exact recovery manifest;
4. repository-wide required assurance, parity, profile assurance, SIQ READY and `OVC merge readiness` pass on the correction PR;
5. after squash merge, the self-hosted post-merge workflow produces the four canonical receipt objects for the correction merge and recovers the bounded prior merge without repeating either physical write.

## Preserved boundaries

No new writer, merge authority, physical gateway, external sink, scientific authority, selector/model/family/candidate/theory promotion, Validation, publication, probability/risk/exposure/trading/execution authority, destructive action, force-push or history rewrite is introduced.

Rollback: forward-supersede only this extractor/workflow binding and preserve all Git history, exact-final logs and any already-persisted content-addressed receipts.

# OVC VIT Live Completion Receipt Runtime Contract v0.1

## Purpose

Close issue `#986` by binding the already-authorised `DSAI_VIT_PHYSICAL_CONTROLLER` / `DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY` materialisation path to the existing canonical `ReceiptStore` completion bundle without introducing a second physical-main writer, merge mechanism or publication authority.

## Authority classification

- Parent authority: `DSAI3V-VIT-GENERAL-AUTHORITY-v0.1`.
- Gate class: `AUTO_RATIFIABLE`.
- Authority delta: `NONE_SAFETY_CONFORMANCE_CORRECTION`.
- Physical-main writer remains exactly `DSAI_VIT_PHYSICAL_CONTROLLER`.
- Physical gateway remains exactly `DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY`.
- This runtime exposes no GitHub merge/write API and cannot approve, merge, force-push, rewrite history or publish to R2.

## Existing receipt sink binding

The production `ReceiptStore` root is fixed to the already-governed operator-local receipts plane:

`OVC_EXTERNAL_ARTIFACT_ROOT/receipts/development/dsai3v`

`OVC_EXTERNAL_ARTIFACT_ROOT` remains process-local, absolute, operator-controlled and disjoint from the repository under `OVC_EXTERNAL_ARTIFACT_ROOT_CONTRACT_v0_1`. No arbitrary path override is exposed. The binding is local persistence only; it grants no R2, release or canonical-publication authority.

A missing, relative, repository-contained or otherwise invalid external root fails closed before a completion receipt is persisted.

## Required live completion chain

A successful eligible physical materialisation is not administratively complete until the following chain is durable:

`PIP -> IntegrationTicket -> VIT generation -> VIT placement -> assurance -> SIQ -> physical main -> PhysicalMaterialisationReceipt -> PacketCompletionReceipt -> canonical DEVOBS completion receipt -> completion/DEVOBS attachment -> ReceiptStore`

The runtime must derive the observed physical tree from the observed Git commit and require exact equality with the current VIT generation result tree. A third/different tree is `POST_WRITE_TREE_MISMATCH` and never becomes completion.

## IntegrationTicket identity

New canonical VIT lineage records must persist an exact content-addressed `IntegrationTicket` and `ticket_id` before permanent physical materialisation. The ticket is additive lineage metadata and does not alter existing PIP, VIT generation or placement identities.

Historical lineage that predates ticket persistence remains readable for historical/status purposes. A live or backfill completion that lacks an exact persisted historical ticket must fail closed as `VIT_COMPLETION_TICKET_ID_MISSING`; the runtime may not reconstruct, guess or infer a ticket identity from ordinal, PR number or surrounding metadata.

## DEVOBS evidence rule

`PacketCompletionReceipt` and its canonical DEVOBS attachment are produced through `ReceiptStore.put_completion_with_devobs`. Only observed source records may populate latency, ORCH, VIT, SIQ or Async Assurance fields. Missing source telemetry remains `UNAVAILABLE`; successful materialisation is not permission to invent timings, retry counts or SIQ receipt identities.

The physical materialisation receipt itself is an observed VIT source and is joined into DEVOBS with exact-tree equality.

## Persistence and recovery

Persistence is recoverable and content-addressed rather than falsely claiming multi-file filesystem atomicity:

1. persist the exact `PhysicalMaterialisationReceipt`;
2. persist the `PacketCompletionReceipt`, canonical DEVOBS record and attachment through the canonical bundle method;
3. rebuild the ReceiptStore index as an integrity check.

An interrupted run is retried with the same exact inputs. Exact duplicate writes are idempotent. Divergent content under an existing logical identity fails `VIT_LEDGER_INTEGRITY_FAIL`. A successful Git write followed by receipt interruption therefore becomes receipt recovery work, not a second physical materialisation.

## Non-authority and prohibitions

This contract grants none of the following:

- another main writer or bypass actor;
- another serialized/parallel merge path;
- repository receipt-bot scope expansion;
- arbitrary local sink selection;
- R2 or release publication;
- operator-gate substitution;
- selector/model/family/candidate/theory promotion;
- scientific, Validation, probability, risk, exposure or execution authority;
- force-push, destructive rollback or history rewrite.

## Activation and rollback

The runtime is eligible for delegated activation only after targeted tests, repository assurance, VIT routing preflight, SIQ/final-head assurance and one live eligible packet demonstrate the complete chain above. Rollback is forward-only: disable the runtime binding while preserving all emitted local receipts and Git history. Existing VIT/SIQ authority remains unchanged.

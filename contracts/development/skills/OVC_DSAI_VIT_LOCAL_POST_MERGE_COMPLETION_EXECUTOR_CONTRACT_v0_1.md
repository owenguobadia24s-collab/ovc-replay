# OVC DSAI3V Local Post-Merge Completion Executor Contract v0.1

Programme: `OVC-DSAI-VIT-v0.3`  
Issue: `#986`  
Authority delta: `NONE`

## Decision

Bind the already-active `DSAI_VIT_PHYSICAL_CONTROLLER` completion-observability obligation to an existing local/self-hosted Windows executor. The executor does **not** perform the Git write and does **not** receive merge authority. It only persists the canonical completion bundle after the existing VIT/SIQ physical path has already advanced `main`.

## Pre-write freeze

For every VIT-mandatory permanent PR, `tests / VIT routing preflight` emits exactly one `OVC_VIT_PHYSICAL_TRANSACTION_FREEZE_B64=` record before physical write eligibility. The record contains the exact `PhysicalMaterialisationTransaction`, PIP/generation/placement identity, base/head/tree identities, controller/gateway identity and completion references.

`ticket_id` and `assurance_frontier_id` are prospectively content-addressed from the exact PR/VIT/CI identities available at freeze time. They are not reconstructed from elapsed time, retry counts or other unavailable telemetry.

A main movement that invalidates the frozen base prevents SIQ readiness and therefore prevents that transaction from becoming physical. A lawful requeue/reanchor produces a new exact freeze for the new placement.

### Administrative closeout rule

A permanent VIT PIP MUST NOT create a second ordinary integration contestant whose packet identity or `completion_transition.next_packet` is an administrative `*CLOSEOUT*` step. For delegated/auto-executable gates, implementation, QA and the delegated decision must be bound before physical write so the PIP can name the substantive successor directly. Post-write commit/tree facts are materialised through `PhysicalMaterialisationReceipt`, `PacketCompletionReceipt` and the associated content-addressed completion bundle.

An operator-required packet may lawfully materialise a `GATE_READY` or equivalent owner-defined state and stop; this rule does not auto-approve that gate. It only prohibits using another ordinary PR to record facts that the post-merge receipt path already owns. Historical PIPs remain immutable and recoverable; this rule is prospective and does not rewrite old lineage.

## Post-merge execution

`.github/workflows/vit-post-merge-completion.yml` runs only from merged `main` content on the existing self-hosted Windows runner. It has read-only GitHub permissions and inherits the operator-local `OVC_EXTERNAL_ARTIFACT_ROOT` from that runner.

The executor:

1. resolves the merged PR associated with the physical commit;
2. retrieves the successful pre-write freeze from the exact PR-head `VIT routing preflight` job log;
3. proves physical parent == frozen predecessor commit;
4. proves physical tree == frozen VIT result tree;
5. validates `OVC_EXTERNAL_ARTIFACT_ROOT` using the existing external-root contract and uses only `<root>/receipts`;
6. calls `recover_effective_write_completion`, which invokes the canonical `persist_physical_completion` path without replaying the Git write;
7. verifies four distinct content-addressed receipt files exist:
   - `PhysicalMaterialisationReceipt`;
   - `PacketCompletionReceipt`;
   - canonical DEVOBS development-latency receipt;
   - completion-observability attachment;
8. writes only auxiliary transaction/proof copies beneath `receipts/transactions/` and `receipts/proofs/`, outside the root receipt index;
9. emits a path-redacted completion proof containing identities only.

Missing runner/root, missing or ambiguous freeze evidence, tree mismatch, missing required GitHub checks, or incomplete ReceiptStore persistence fails closed. `workflow_dispatch` is an idempotent recovery route for an already-effective main write.

## Telemetry

Only observed source fields are populated. Missing timings, retries, assurance durations, ticket timings and latency decomposition remain `UNAVAILABLE`/null through the canonical DEVOBS builder.

## Security and authority

This contract creates no new main writer, merge adapter, gateway, cloud sink, Drive/R2 publication path, scientific authority, Validation authority, probability/risk/exposure authority, execution authority, force-push or history-rewrite capability.

The existing physical writer remains `DSAI_VIT_PHYSICAL_CONTROLLER`; the existing gateway remains `DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY`; physical main remains the court record.

## Completion criterion for #986

Do not close #986 from code presence alone. Close only after one live eligible VIT packet produces a successful self-hosted post-merge run whose proof reports exact tree equality and all four required content-addressed receipt objects present in the existing `OVC_EXTERNAL_ARTIFACT_ROOT/receipts` store.

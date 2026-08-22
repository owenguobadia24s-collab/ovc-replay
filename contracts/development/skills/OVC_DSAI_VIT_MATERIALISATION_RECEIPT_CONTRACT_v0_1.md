# OVC DSAI v0.3 Physical Materialisation & Receipt Contract v0.1

Authority: implementation and isolated rehearsal only. Live physical-main control remains denied until `DSAI3V-G-VIT-PILOT` operator PASS.

Each physical attempt is an immutable `PhysicalMaterialisationTransaction` (PMT) binding exact VIT generation, train/ticket identity, expected predecessor/result tree, authority/assurance frontier, materialisation profile and attempt number. Multiple attempts may exist for the same unchanged VIT generation; attempt history is append-only.

The implementation gateway supports `ISOLATED_REHEARSAL` only before the pilot gate. A request for `LIVE_PHYSICAL_MAIN` fails closed with `WAITING_OPERATOR_AUTHORITY`. Parallel materialisation is prohibited; the gateway models one exclusive lease identity per expected predecessor.

After an isolated write, exact tree equality is mandatory. `PhysicalMaterialisationReceipt` binds transaction ID, observed commit/tree and equality result. `PacketCompletionReceipt` binds implementation, QA, gate, PIP, VIT, materialisation and successor provenance without requiring a second ordinary base-sensitive closeout PR.

`ReceiptStore` is content-addressed and append-only. Exact duplicate write is idempotent; same logical ID with divergent content is `VIT_LEDGER_INTEGRITY_FAIL`. Receipt resolution is by transaction and generation-qualified packet-completion indexes derived from normative receipt bytes and rebuildable from the store. Bare `packet_id` is not a globally unique completion identity across remediation, review and recovery history.

Crash/unknown-write recovery is fail-closed: observed predecessor means `WRITE_NOT_EFFECTIVE_RETRYABLE`; observed exact expected result means `WRITE_EFFECTIVE_RECEIPT_RECOVERY_REQUIRED`; any third tree means `POST_WRITE_STATE_UNKNOWN` / repository integrity incident. Unknown state never becomes completion.

Existing SIQ remains the serialized physical gateway for live main. This packet does not activate the VIT writer registry entry.

# OVC DSAI3V Canonical Completion Receipt v2 Contract v0.1

Status: prospective, authority-inert observability extension.
Authority delta: NONE.

## Historical immutability

`ovc-development-latency-canonical-dsai3v/v1` and its existing required completion bundle remain valid and unchanged. No historical v1 receipt, record ID, hash, attachment, completion receipt, materialisation receipt or completion proof may be rewritten or regenerated under v2.

## Prospective v2

New DSAI3V completions may emit `ovc-development-latency-canonical-dsai3v/v2` in addition to the existing v1 required bundle. A narrowly versioned `ovc-dsai3v-completion-observability-attachment/v2` is used for v2. This is necessary because the existing ReceiptStore index gives the v1 attachment an unqualified completion-receipt index key; reusing v1 for a second attachment would collide or require mutating historical v1 index semantics. V1 attachment behavior remains unchanged.

V2 timestamps are UTC RFC3339, source-bound and directly observed. Missing evidence remains null. Each non-null canonical timing field must have an `OBSERVATIONAL_ONLY` source row. Source precedence is: exact owner receipt; exact GitHub PR/job/check evidence; durable DEVOBS; exact log; otherwise null. V2 never infers one event time from another.

Canonical timing fields are PR opened, AA0 exact-reuse observed, profile PASS, SIQ READY, merge-readiness PASS, physical materialisation, packet-completion persistence and completion-proof persistence. Status is `OBSERVED_COMPLETE`, `OBSERVED_PARTIAL` or `UNAVAILABLE`.

Mandatory ordering is checked only where both endpoints are observed. Impossible authoritative ordering is preserved raw and emits `SOURCE_TIMESTAMP_ORDER_INVALID`; unsafe derived latency is null. Negative latency is never emitted.

V2 identity is SHA-256 over canonical logical content under the dedicated v2 identity role. Same logical inputs yield the same record ID; a timestamp or provenance change yields a different ID.

## Storage and authority

V2 uses the existing bound `ReceiptStore` and external receipt root. Content-addressed append-only semantics remain exact. There is no new database, daemon, queue, event bus, control plane, repository fallback or physical writer. Authority effect is always `NONE`.

## Rollback

Rollback is forward-only: stop future v2 emission and restore the prior writer path while preserving all v1/v2 receipts, attachments, proofs and Git history.

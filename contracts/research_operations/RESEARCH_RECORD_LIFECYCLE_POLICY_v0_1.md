# Research Record Lifecycle Policy v0.1

Status: `FROZEN_AFTER_RO_WP1`

Lifecycle states are:

```text
DRAFT -> FROZEN -> ADJUDICATED
              -> SUPERSEDED
DRAFT -> WITHDRAWN
```

A frozen or adjudicated record is immutable. Correction creates a new record whose `lineage.supersedes` points to the predecessor. The predecessor canonical bytes remain unchanged; superseded status is derived from the successor lineage.

The following are prohibited:

- frozen-record overwrite or deletion;
- identity reuse for changed content;
- rename to evade identity checks;
- mutation of OPT-A, C1 or C2 records;
- hidden repair, substitution or post-cutoff enrichment.

Freeze validates the envelope, record type, cutoff, Validation lock, lineage and payload. It then assigns `frozen_at`, deterministic `record_id` and `content_sha256`.

Only a frozen claim may later be adjudicated. Adjudication references the frozen claim and neutral realization without changing either source.

RO-WP1 provides pure functions only. Durable storage, audit emission and operator commands remain RO-WP2 work after RO-G1.
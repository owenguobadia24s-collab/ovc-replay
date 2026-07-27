# C2 First Prospective Evidence Batch Review Contract v0.1

## Purpose

This contract governs the first review of records accumulated under `RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1` after C2-G7 accepted bounded prospective evidence accumulation.

## Entry condition

The review may classify a batch as prospectively reviewable only when the declared append target contains at least one valid `LIVE_PROSPECTIVE` record created after C2-G7. Valid `TIME_GATED_REPLAY` and `NON_EVIDENTIARY_REPLAY` rows may coexist in the ledger, but they do not satisfy the first-real-prospective-batch condition. Fixtures, examples and gate packets are not evidence records.

## Batch identity

A reviewable batch must declare:

- one immutable `batch_id`;
- ordered live-prospective record IDs;
- total record count, live-prospective count, operation-mode counts and class counts;
- SHA-256 over the exact canonical JSONL bytes;
- first market-window start and last market-window end;
- first-valid trigger-time range;
- first and last `review_created_at_utc`;
- the exact active C2 release and manifest;
- the source commit and evidence-ledger location.

## Record acceptance

Every row must:

- validate against `schemas/opt_b/c2/c2_prospective_evidence_record_v0_2.schema.json`;
- bind `RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1`;
- bind the exact active Discovery release and manifest;
- declare `market_window_start_utc`, `market_window_end_utc`, `trigger_first_valid_at`, `review_created_at_utc` and `operation_mode`;
- use one permitted record class and evidence status;
- contain non-empty source-object lineage;
- contain no Validation, C2E, probability, exposure, trading or execution authority;
- contain no prohibited historical seed material.

A row counts toward the first prospective batch only when `operation_mode` is `LIVE_PROSPECTIVE` and its market window and first-valid trigger are strictly after C2-G6. Replay rows remain separately counted and cannot be converted into prospective rows.

Duplicate active record IDs, malformed JSON, missing lineage, invalid chronology, pre-cutoff live rows or mixed selector identity make the ledger non-reviewable.

## Review outcomes

- `PASS_FIRST_BATCH_ACCEPTED`: at least one valid `LIVE_PROSPECTIVE` record exists and every ledger row passes integrity and authority checks.
- `DEFER_NO_REAL_PROSPECTIVE_BATCH`: the append target is absent, empty or contains no valid `LIVE_PROSPECTIVE` row.
- `BLOCK_BATCH_INTEGRITY_FAILURE`: one or more rows fail schema, identity, chronology, cutoff, lineage, authority or duplicate checks.

A `DEFER` result is not a failure and must not be converted into synthetic evidence. A `BLOCK` result preserves the submitted bytes and records the reasons; it does not rewrite rows.

## Authority boundary

This review may accept or defer a compact batch for continued descriptive research only. It grants no C2E, C2.5, C3, OPT-C, OPT-D, Validation, probability, exposure, trading or execution authority. It cannot mutate selectors, releases or R2 objects.

## Next boundary

After `PASS_FIRST_BATCH_ACCEPTED`, the next boundary is `FIRST_PROSPECTIVE_EVIDENCE_INTERPRETIVE_REVIEW`. After `DEFER_NO_REAL_PROSPECTIVE_BATCH`, the next boundary is `CAPTURE_FIRST_REAL_PROSPECTIVE_EVIDENCE_BATCH`.

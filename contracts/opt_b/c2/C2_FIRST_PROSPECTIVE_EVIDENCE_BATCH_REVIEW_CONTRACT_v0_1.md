# C2 First Prospective Evidence Batch Review Contract v0.1

## Purpose

This contract governs the first review of records accumulated under `RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1` after C2-G7 accepted bounded prospective evidence accumulation.

## Entry condition

The review may classify a batch as reviewable only when the declared append target exists and contains at least one real record produced after C2-G7. Fixtures, examples, historical rows and gate packets are not evidence records.

## Batch identity

A reviewable batch must declare:

- one immutable `batch_id`;
- ordered record IDs;
- record count and class counts;
- SHA-256 over the exact canonical JSONL bytes;
- first and last observation timestamps;
- first and last creation timestamps;
- the exact active C2 release and manifest;
- the source commit and evidence-ledger location.

## Record acceptance

Every row must:

- validate against `schemas/opt_b/c2/c2_prospective_evidence_record_v0_1.schema.json`;
- bind `RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1`;
- bind the exact active Discovery release and manifest;
- be strictly prospective under the WP7 cutoff;
- use one permitted record class and evidence status;
- contain non-empty source-object lineage;
- contain no Validation, C2E, probability, exposure, trading or execution authority;
- contain no prohibited historical seed material.

Duplicate active record IDs, malformed JSON, missing lineage, pre-cutoff rows or mixed selector identity make the batch non-reviewable.

## Review outcomes

- `PASS_FIRST_BATCH_ACCEPTED`: at least one real record exists and every row passes integrity and authority checks.
- `DEFER_NO_REAL_PROSPECTIVE_BATCH`: the append target is absent or contains zero real records.
- `BLOCK_BATCH_INTEGRITY_FAILURE`: one or more rows fail schema, identity, cutoff, lineage, authority or duplicate checks.

A `DEFER` result is not a failure and must not be converted into synthetic evidence. A `BLOCK` result preserves the submitted bytes and records the reasons; it does not rewrite rows.

## Authority boundary

This review may accept or defer a compact batch for continued descriptive research only. It grants no C2E, C2.5, C3, OPT-C, OPT-D, Validation, probability, exposure, trading or execution authority. It cannot mutate selectors, releases or R2 objects.

## Next boundary

After `PASS_FIRST_BATCH_ACCEPTED`, the next boundary is `FIRST_PROSPECTIVE_EVIDENCE_INTERPRETIVE_REVIEW`. After `DEFER_NO_REAL_PROSPECTIVE_BATCH`, the next boundary is `CAPTURE_FIRST_REAL_PROSPECTIVE_EVIDENCE_BATCH`.
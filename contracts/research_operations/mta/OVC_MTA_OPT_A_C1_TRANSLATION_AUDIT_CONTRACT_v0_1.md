# OVC MTA OPT-A and C1 Translation Audit Contract v0.1

## Purpose

Account for every lawful source interval, derived 15M/2H_A_L bar and C1 record in the frozen June full-month replay without changing source data, formulas, thresholds, selectors or releases.

## Authority

This contract authorises read-only verification and compact audit evidence only. It does not authorise provider intake, repair, interpolation, gap filling, source replacement, formula change, selector mutation, publication, Validation consumption, C2E, C2.5, C3, probability, risk, exposure or execution.

## Frozen subject

- Run: `PD-JUNE-FM.RUN.9810cfa8a2e2930be2e503b9`
- Source slice: `RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1`
- Source logical SHA-256: `1578b555f3d5aa2822b603141261f86a047096030e5faacd4380ef2c6d4f52e3`
- Replay payload logical SHA-256: `d784f47395d904b2d78d77cde0a8a40287877692d8b92889ab2eeedef621a24b`
- Target: `[2026-06-01T00:00:00Z, 2026-07-01T00:00:00Z)`
- Context: `[2026-05-30T00:00:00Z, 2026-07-03T00:00:00Z)`
- Clocks: `15M`, `2H_A_L`
- Sides: `BID`, `ASK`

## Source audit

The audit must verify the accepted source inventory, exact file hashes, row counts, timestamp ordering, duplicate counts, side pairing, gap-run counts and accepted paired-provider-absence policy. Source discontinuities are classified only from frozen source QA evidence:

- `PAIRED_PROVIDER_ABSENCE`
- `SCHEDULED_CLOSURE`
- `SOURCE_PARTITION_BOUNDARY`
- `UNKNOWN_DISCONTINUITY`

No absent interval may be fabricated or bridged.

## Derived-bar audit

For each clock and side, verify:

- exact file byte hash and record count;
- unique, monotonic bar identity;
- exact clock duration;
- exact BID/ASK interval, quality and parent-count pairing;
- `COMPLETE` bars have exact parent cardinality and non-null OHLCV;
- `QUARANTINED_INCOMPLETE_PARENT_SET` bars have deficient parent cardinality and null OHLCV;
- target/context eligibility is preserved;
- every record is accounted for.

## C1 audit

For every C1 record, verify:

- exact one-to-one parentage to a `COMPLETE` derived bar;
- no C1 output from an incomplete bar;
- source path, source-bar identity, timestamps, prices and M1 parent lineage;
- formula registry identity `C1.FORMULAS.v0.1`;
- Decimal recomputation of all measurements, categorical direction and null reasons;
- deterministic C1 record identity;
- lawful prior use only across contiguous complete bars;
- exact target/context eligibility;
- complete BID/ASK interval pairing.

## Accounting invariant

`complete derived bars == C1 records` and `incomplete derived bars == C1 exclusions` for every stream. The full audit must report an exact inspected count and `unaccounted_derived_records = 0`.

## External evidence

Full payloads remain outside Git. The repository stores a compact audit packet containing input Drive IDs, sizes, SHA-256 hashes, aggregate and weekly counts, check results, findings, external audit ID and Drive file ID. A missing or hash-mismatched external artifact makes MTA-G2 `NOT_REPRODUCIBLE`.

## Determinism

The audit output is canonical JSON. Repeating the audit over identical bytes and the same implementation version must reproduce the same logical SHA-256. Generated timestamps are excluded from the logical subject hash or fixed by the run manifest.

## Acceptance

MTA-G2 passes only when:

1. every required source/bar/C1 byte hash matches the frozen manifests;
2. all source rows and all 10,178 derived bar/C1 records are accounted for;
3. every complete bar maps to exactly one valid C1 record;
4. no incomplete bar maps to C1;
5. formula, null, identity, serialization and lineage mismatch counts are zero;
6. paired provider absences and incomplete buckets remain explicitly censored;
7. focused, retained and complete repository assurance pass;
8. QA recommends PASS with no unresolved blocking issue.

## Rollback

Supersede through a new audit version bound to immutable input hashes. Preserve this contract, source bytes, audit artifact, findings and decision record; never rewrite the source or C1 outputs.

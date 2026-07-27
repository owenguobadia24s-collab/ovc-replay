# RPS Gapped Source Acceptance Contract v0.1

## Identity and authority

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP2`
- Proposed gate: `RPS-G1B`
- Provider: `DUKASCOPY`
- Instrument: `GBPUSD`
- Slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`
- Source interval: `[2026-06-22T00:00:00Z, 2026-06-25T00:00:00Z)`
- Source quarantine: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1.20260727T160337Z.38a69acd`

This contract applies only to checksum-pinned, no-network re-evaluation of the exact June quarantine above. It does not authorise another provider request, a different quarantine, a different interval, or arbitrary local-path input.

## Admissible GAPPED state

`coverage_state: GAPPED` may be frozen only when every condition below passes:

1. M1 BID contains exactly 4,285 rows, 35 explicitly absent timestamps and 24 gap runs.
2. M1 ASK contains exactly 4,285 rows and has the identical timestamp set, absent timestamps and gap runs.
3. Both M1 sides retain the exact first and last expected timestamps.
4. Neither M1 side contains a duplicate or non-monotonic timestamp.
5. Native H1 BID and ASK each contain exactly 72 ordered rows with complete interval boundaries.
6. M1 and H1 BID/ASK timestamp pairing and price-order checks pass.
7. Exactly 64 complete M1-derived H1 bars per side are comparable to native H1; every comparison has identical OHLC and no native timestamp is missing.
8. Every absent M1 timestamp and every gap run is written to immutable QA evidence.
9. Every 15M, M1-derived H1 and 2H parent containing an absent M1 member is marked `UNAVAILABLE_INCOMPLETE_M1_PARENT` and excluded.
10. No source row or parent is forward-filled, interpolated, repaired, zero-filled or synthesized.

A different row count, missing count, gap-run count, cross-side timestamp set, boundary, native-H1 inventory or reconciliation result is `BLOCK` and cannot be accepted under RPS-G1B.

## Checksum and copy boundary

Before a freeze:

- the exact quarantine must contain only its original incident record and eight expected BI5 transport objects;
- every file is measured and hashed locally;
- the resulting checksum inventory is stored outside the source quarantine;
- transport byte sizes must match the operator diagnostic;
- the complete inventory receives a canonical SHA-256.

The freeze command re-hashes the source quarantine, verifies the inventory, copies transport bytes into a new staging directory and verifies every copied size and hash. The source quarantine is measured before and after the copy and must be byte-identical. It is never renamed, relabelled, overwritten or used as the accepted destination.

## Failure evidence

Gap, BID/ASK, native-H1 and downstream-coverage receipts are written before the recovery pass/fail branch. If a condition fails, the recovery staging directory is quarantined with those receipts preserved. No accepted slice is created.

## Frozen result

A passing result may create one local immutable source slice with:

- `coverage_state: GAPPED`;
- `frozen: true`;
- `release_status: NOT_A_RELEASE`;
- `selector_eligibility: NONE`;
- `r2_publication: DENIED`;
- Validation consumption denied;
- LIVE_PROSPECTIVE append denied.

## Retained prohibitions

RPS-G1B grants no ACTIVE_RESEARCH_TRIAGE, live Pattern Discovery processing, active novelty ranking, semantic or theory promotion, selector change, release creation, R2 publication, Validation consumption, C2E/C2.5/C3, OPT-C/OPT-D, probability, risk, exposure, trading, execution or agent-write authority.

## Rollback

Before a frozen GAPPED slice exists, close the amendment PR or revert its merge and withdraw RPS-G1B recovery authority. Preserve the original July and June quarantines and every generated checksum or failure receipt. Never rewrite external evidence.

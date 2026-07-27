# RPS-WP2 — Frozen GAPPED Source Evidence QA

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP2`
- Gate: `RPS-G2`
- Baseline main: `18ba74378ece734647801576f373d68b4ba8687f`
- Slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`
- Interval: `[2026-06-22T00:00:00Z, 2026-06-25T00:00:00Z)`
- Coverage: `GAPPED`
- QA recommendation: `PASS`

## Compact evidence received

The operator supplied one source-slice manifest and eight compact receipts. The repository records their exact file byte sizes and SHA-256 values in `RPS_WP2_COMPACT_EVIDENCE_INDEX.json`. Raw BI5 transport objects, CSV source objects and machine paths were not received or committed.

## Independent consistency checks

1. The canonical manifest logical hash recomputes to `429b7b568b7a43d04893c1873773f0b1b567730f2d5d4122d6a1c06dd40e3e41`.
2. The manifest file SHA-256 recomputes to `8509b6cc66814663786e429e6ba1dc0c3497482fc6ac8ceb016cfc1867ec78eb` and matches the freeze receipt.
3. The quarantine inventory logical hash recomputes to `ce58bc91ea36e920fa2f855a96ee7084e5d867b976a0d06a9e94bf65b20084c2` and matches both the provider provenance and freeze receipts.
4. The manifest and source-object inventory agree on all four object IDs, clocks, sides and SHA-256 values.
5. Every compact evidence file is byte-size and SHA-256 pinned in the evidence index.

## Source-object result

| Clock | Side | Rows | First | Last | Result |
|---|---:|---:|---|---|---|
| M1 | BID | 4,285 | 2026-06-22 00:00Z | 2026-06-24 23:59Z | PASS_GAPPED |
| M1 | ASK | 4,285 | 2026-06-22 00:00Z | 2026-06-24 23:59Z | PASS_GAPPED |
| H1 | BID | 72 | 2026-06-22 00:00Z | 2026-06-24 23:00Z | PASS |
| H1 | ASK | 72 | 2026-06-22 00:00Z | 2026-06-24 23:00Z | PASS |

## QA result

- M1 BID and ASK expose the same 35 absent timestamps in 24 runs.
- Boundaries are complete; duplicates and non-monotonic timestamps are zero.
- BID/ASK pairing passes for 4,285 M1 and 72 H1 rows, with no missing counterpart or inverted row.
- Native H1 reconciliation passes for 64 complete M1-derived hours per side with no missing native timestamp and no OHLC mismatch.
- Downstream coverage is explicit: 271/288 15M parents, 64/72 M1-derived H1 parents and 30/36 2H parents are available.
- The 17 incomplete 15M parents, 8 incomplete M1-derived H1 parents and 6 incomplete 2H parents are unavailable and excluded.
- No repair, forward fill, interpolation or synthesis occurred.
- The source quarantine remained unchanged after copy-on-verify.

## Authority assessment

The acceptance delta is wholly inside the operator-approved `RPS-G1B` envelope. It records that the exact named local source slice passed the already-approved GAPPED conditions. It does not grant a new provider request, activate a selector, create a release, publish R2, consume Validation, append LIVE_PROSPECTIVE evidence, enable ACTIVE_RESEARCH_TRIAGE, promote semantics or grant probability, risk, exposure, trading, execution or agent-write authority.

## Warnings

The source remains GAPPED. Missing M1 rows are absent evidence, not zero-volume candles. Every downstream command must consume the coverage receipt and reject incomplete parents.

## Rollback

Revert the RPS-WP2/RPS-G2 evidence-acceptance merge and return the programme state to `RPS_G1B_APPROVED_AWAITING_CHECKSUM_PINNED_LOCAL_FREEZE`. Preserve the immutable local slice, both original quarantines and all compact evidence. Rollback does not delete or rewrite external evidence.

## Recommendation

`PASS` — complete RPS-WP2, auto-ratify RPS-G2 under delegated non-reserved authority and make RPS-WP3 eligible for derived local prospective compute only.

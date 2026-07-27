# RPS-G1A June Source-QA Incident

- Incident ID: `RPS.INCIDENT.DUKASCOPY.GBPUSD.20260622_20260625.M1_GAPPED.v1`
- Source gate: `RPS-G1A`
- Slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`
- Interval: `[2026-06-22T00:00:00Z, 2026-06-25T00:00:00Z)`
- Operator-local quarantine ID: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1.20260727T160337Z.38a69acd`
- Accepted source slice created: `false`
- Provider retry requested: `false`
- Raw bytes committed to Git: `false`

## Trigger

The RPS-G1A operator-local intake downloaded the approved June M1 BID/ASK and native H1 BID/ASK transport objects. The command then quarantined the staging workspace because the frozen RPS-G1A policy treated every non-weekend M1 absence as a blocking gap.

## Operator diagnostic evidence

| Check | Result |
|---|---|
| M1 BID | 4,285 rows; 35 absent minutes; 24 gap runs |
| M1 ASK | 4,285 rows; identical timestamp set and absences |
| M1 boundaries | Complete from `2026-06-22T00:00:00Z` to `2026-06-24T23:59:00Z` |
| Ordering | No duplicate or non-monotonic timestamps |
| BID/ASK | Exact timestamp pairing; no inverted price rows |
| Native H1 | 72 BID and 72 ASK rows; complete boundaries |
| H1 reconciliation | 64 complete M1-derived H1 bars per side; all present natively; zero OHLC mismatches |

The diagnostic therefore establishes an internally consistent but M1-gapped provider source. It does not establish why Dukascopy omitted the 35 M1 records and does not authorise their reconstruction.

## Transport inventory observed by the operator

| Relative provider object | Bytes |
|---|---:|
| `GBPUSD/2026/05/22/BID_candles_min_1.bi5` | 11,210 |
| `GBPUSD/2026/05/23/BID_candles_min_1.bi5` | 10,791 |
| `GBPUSD/2026/05/24/BID_candles_min_1.bi5` | 10,740 |
| `GBPUSD/2026/05/BID_candles_hour_1.bi5` | 6,492 |
| `GBPUSD/2026/05/22/ASK_candles_min_1.bi5` | 11,226 |
| `GBPUSD/2026/05/23/ASK_candles_min_1.bi5` | 10,748 |
| `GBPUSD/2026/05/24/ASK_candles_min_1.bi5` | 11,098 |
| `GBPUSD/2026/05/ASK_candles_hour_1.bi5` | 6,518 |

Exact SHA-256 values remain unknown to GitHub and must be calculated locally by the checksum-inventory command before any re-evaluation.

## Disposition

- Status: `QUARANTINED_NO_ACCEPTED_SOURCE_SLICE`
- Recommended action: operator amendment `RPS-G1B`
- Source quarantine: preserve unchanged
- Missing minutes: record explicitly
- Repairs, interpolation, forward fill and synthesis: prohibited
- Dependent incomplete 15M, M1-derived H1 and 2H parents: unavailable and excluded

## Retained authority boundary

This incident record grants no GAPPED acceptance, provider retry, release, selector, R2, Validation, LIVE_PROSPECTIVE, ACTIVE_RESEARCH_TRIAGE, semantic, probability, risk, exposure, trading, execution or agent-write authority.

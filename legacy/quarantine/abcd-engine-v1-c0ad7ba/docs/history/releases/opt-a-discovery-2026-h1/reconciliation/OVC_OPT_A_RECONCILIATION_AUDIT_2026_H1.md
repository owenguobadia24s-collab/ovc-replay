# OPT-A Reconciliation Audit — GBP/USD 2026 H1

**Audit ID:** `OPT-A.RECON.GBPUSD.2026H1.v0.1`  
**Status:** PASS WITH RESOLUTION-SPECIFIC AUTHORITY  
**Scope:** GBP/USD BID, UTC, `[2026-01-01, 2026-07-01)`  
**Method boundary:** Read-only comparison; no source row or accepted bar was modified, repaired, or filled.

## Executive finding

The 209-bar difference is fully reconciled. It is an acceptance-policy difference, not a price disagreement.

- Hourly source accepted 2H bars: **1,521**
- Complete minute-chain 2H bars: **1,312**
- Accepted by both paths: **1,312**
- Hourly-only bars: **209**
- Minute-only bars: **0**
- Common bars with exact OHLC agreement: **1,312/1,312**
- Hourly-only bars where available minutes reproduce the hourly OHLC: **209/209**
- Total absent minute records inside the hourly-only bars: **780**

Every minute-chain bar is a subset of the hourly-derived release. No common bar differs in open, high, low, or close. Each hourly-only bar contains 1–15 absent minute records, but the provider-returned minutes that remain reproduce the accepted hourly OHLC exactly.

This does **not** authorize reconstruction of the absent minute records. It demonstrates that the direct provider hourly candles remain valid independent source objects for the 2H spine.

## Cause classification

| Class | Count | Determination |
|---|---:|---|
| Accepted by both, exact OHLC | 1,312 | Fully corroborated |
| Accepted by H1 path only, sparse M1, price-equivalent | 209 | Valid for 2H from H1; invalid for complete M1/15M claims |
| Accepted by H1 path only, price disagreement | 0 | None found |
| Accepted by M1 path only | 0 | None found |
| Rejected by both aggregators | 31 | Retain rejection; predominantly fixed-UTC boundary/session alignment |
| H1 rejected and not enumerated by M1 candidate buckets | 2 | Retain rejection; no authority gained from candidate-list asymmetry |

The direct M1 retrieval intentionally excluded synthesized flat candles. Therefore, an absent one-minute candle can represent a provider-returned sparse/no-tick interval rather than a corrupt hourly candle. The audit makes no causal claim about individual gaps; it relies only on exact price equivalence and source independence.

## Concentration of the 209 hourly-only bars

### By month

| Month | Bars |
|---|---:|
| 2026-01 | 43 |
| 2026-02 | 34 |
| 2026-03 | 22 |
| 2026-04 | 42 |
| 2026-05 | 35 |
| 2026-06 | 33 |

### By fixed UTC TPO bucket

| Bucket | Bars |
|---|---:|
| TPO-A | 5 |
| TPO-B | 8 |
| TPO-C | 15 |
| TPO-D | 2 |
| TPO-E | 1 |
| TPO-F | 1 |
| TPO-G | 1 |
| TPO-I | 1 |
| TPO-J | 5 |
| TPO-K | 81 |
| TPO-L | 89 |

`TPO-K` `[20:00,22:00)` and `TPO-L` `[22:00,00:00)` contain **170/209** exceptions. This is a structural concentration near the provider's low-activity/weekly-boundary region; it is not treated as proof of an economic cause.

## Authority decision

OPT-A should use resolution-specific source authority:

1. **Canonical 2H price spine:** provider H1 candles aggregated deterministically as two exact UTC H1 bars.
2. **Canonical 15M detail:** provider-returned M1 candles aggregated only when all 15 exact minute records exist.
3. **No cross-resolution fabrication:** an H1 or 2H bar must never generate missing M1 or 15M records.
4. **No silent repair:** incomplete 15M buckets remain quarantined; the 209 H1-authorized 2H bars carry an explicit `M1_DETAIL_INCOMPLETE` quality flag.
5. **Boundary exclusions remain:** the 33 H1-rejected 2H buckets are not promoted, including the 31 also rejected by the minute chain.

This preserves the no-fill doctrine while avoiding the false conclusion that a 2H bar is unusable merely because a non-flat M1 export omitted a minute candle.

## OPT-A closure state

**Reconciliation verdict:** `PASS`  
**Proposed OPT-A state:** `RECONCILED — READY TO SEAL AFTER OPERATOR REVIEW`

The audit closes the 209-bar discrepancy. Sealing OPT-A should bind:

- the two raw source releases and hashes;
- the resolution-specific authority rule above;
- the complete exception ledger;
- explicit `M1_DETAIL_COMPLETE` / `M1_DETAIL_INCOMPLETE` lineage flags;
- preservation of every rejected bucket;
- a rerun check proving identical counts and hashes.

No OPT-B term was recomputed during this audit.

## Reproducibility files

- `opt_a_reconciliation_summary.json` — machine-readable verdict and counts.
- `opt_a_2h_reconciliation_ledger.csv` — all 1,521 accepted canonical 2H bars with lineage status.
- `opt_a_hourly_only_exceptions.csv` — all 209 H1-only bars and exact missing-minute ranges.

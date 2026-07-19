# OVC OPT-C Neutral Forward-Outcome Measurement Report v0.1

**Status:** `MEASUREMENT COMPLETE — DESCRIPTIVE ONLY — NOT AN EDGE CLAIM`  
**Measurement contract:** `OPT-C-MEASURE-0.1.1`  
**Measured complete event–horizon pairs:** **26,334**

## Strict measured coverage

| Event clock | 1h | 2h | 4h | 8h | 12h | Total |
|---|---:|---:|---:|---:|---:|---:|
| 15M | 7,193 | 6,729 | 5,925 | 4,125 | 2,361 | 26,333 |
| 2H | 1 | 0 | 0 | 0 | 0 | 1 |

Only coverage records marked `COMPLETE` at 1h, 2h, 4h, 8h and 12h were measured. Censored paths received no outcome row. The 24h horizon remains coverage-only and 48h remains blocked.

## Neutral descriptive medians

| Event clock | Horizon | Raw return | Up excursion | Down excursion | Direction-normalized return |
|---|---:|---:|---:|---:|---:|
| 15M | 1h | 0.200 pips | 7.400 pips | 7.300 pips | -0.400 pips |
| 15M | 2h | 0.700 pips | 11.200 pips | 11.000 pips | -0.600 pips |
| 15M | 4h | 1.100 pips | 17.200 pips | 16.800 pips | -1.000 pips |
| 15M | 8h | 3.100 pips | 26.800 pips | 24.700 pips | -2.500 pips |
| 15M | 12h | 3.900 pips | 34.200 pips | 29.600 pips | 0.200 pips |
| 2H | 1h | 17.6 pips | 31.4 pips | 0E+4 pips | None pips |
| 2H | 2h | None pips | None pips | None pips | None pips |
| 2H | 4h | None pips | None pips | None pips | None pips |
| 2H | 8h | None pips | None pips | None pips | None pips |
| 2H | 12h | None pips | None pips | None pips | None pips |

These are overlapping structural-event observations. They are not independent samples and are not wins, losses, trades, expected returns or evidence of profitability.

## Lineage and reproducibility

Every row binds the event anchor, coverage record, ordered 15M path, endpoint ratified 15M B-state and all intervening 15M state transitions. All prices are sealed provider BID values; no missing interval was filled.

## Next gate

Run the independent semantic sanity review: verify measure distributions, overlap strata, family/direction support and frontier applicability before any OPT-D cohort construction.

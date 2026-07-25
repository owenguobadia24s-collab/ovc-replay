# OVC OPT-C Neutral Forward-Outcome Measurement Report v0.1

**Status:** `MEASUREMENT COMPLETE — DESCRIPTIVE ONLY — NOT AN EDGE CLAIM`  
**Measurement contract:** `OPT-C-MEASURE-0.1.1`  
**Measured complete event–horizon pairs:** **14,979**

## Strict measured coverage

| Event clock | 1h | 2h | 4h | 8h | 12h | Total |
|---|---:|---:|---:|---:|---:|---:|
| 15M | 3,605 | 3,386 | 2,984 | 2,125 | 1,282 | 13,382 |
| 2H | 416 | 390 | 338 | 261 | 192 | 1,597 |

Only coverage records marked `COMPLETE` at 1h, 2h, 4h, 8h and 12h were measured. Censored paths received no outcome row. The 24h horizon remains coverage-only and 48h remains blocked.

## Neutral descriptive medians

| Event clock | Horizon | Raw return | Up excursion | Down excursion | Direction-normalized return |
|---|---:|---:|---:|---:|---:|
| 15M | 1h | -0.300 pips | 6.900 pips | 7.400 pips | -0.100 pips |
| 15M | 2h | -0.100 pips | 10.400 pips | 10.900 pips | -0.100 pips |
| 15M | 4h | -0.300 pips | 16.000 pips | 17.100 pips | 0.150 pips |
| 15M | 8h | -1.500 pips | 25.500 pips | 25.900 pips | -0.550 pips |
| 15M | 12h | -0.850 pips | 33.900 pips | 32.750 pips | 1.100 pips |
| 2H | 1h | 0.400 pips | 6.800 pips | 6.200 pips | 0.450 pips |
| 2H | 2h | -0.500 pips | 9.800 pips | 9.000 pips | 0.900 pips |
| 2H | 4h | -1.050 pips | 14.450 pips | 14.450 pips | -0.150 pips |
| 2H | 8h | -2.300 pips | 20.400 pips | 22.400 pips | -0.400 pips |
| 2H | 12h | -6.000 pips | 26.550 pips | 27.750 pips | -2.800 pips |

These are overlapping structural-event observations. They are not independent samples and are not wins, losses, trades, expected returns or evidence of profitability.

## Lineage and reproducibility

Every row binds the event anchor, coverage record, ordered 15M path, endpoint ratified 15M B-state and all intervening 15M state transitions. All prices are sealed provider BID values; no missing interval was filled.

## Next gate

Run the independent semantic sanity review: verify measure distributions, overlap strata, family/direction support and frontier applicability before any OPT-D cohort construction.

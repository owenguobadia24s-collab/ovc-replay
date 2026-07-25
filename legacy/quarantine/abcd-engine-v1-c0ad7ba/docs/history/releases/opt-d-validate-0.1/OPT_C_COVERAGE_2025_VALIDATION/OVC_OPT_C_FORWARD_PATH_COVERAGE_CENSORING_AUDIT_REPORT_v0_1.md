# OVC OPT-C Strict Forward-Path Coverage and Censoring Audit

**Status:** `AUDIT COMPLETE — PARTIAL MEASUREMENT READINESS — 48H BLOCKED`  
**Coverage contract:** `OPT-C-COVERAGE-0.1`  
**Forward price values read:** `NO`

## Coverage by horizon

| Clock | Horizon | Complete | Censored | Complete rate | Overlap rate |
|---|---:|---:|---:|---:|---:|
| 15M | 1h | 7,193 | 447 | 94.15% | 88.43% |
| 15M | 2h | 6,729 | 911 | 88.08% | 94.74% |
| 15M | 4h | 5,925 | 1,715 | 77.55% | 96.37% |
| 15M | 8h | 4,125 | 3,515 | 53.99% | 97.96% |
| 15M | 12h | 2,361 | 5,279 | 30.90% | 98.85% |
| 15M | 24h | 64 | 7,576 | 0.84% | 99.29% |
| 15M | 48h | 0 | 7,640 | 0.00% | 99.31% |
| 2H | 1h | 1 | 0 | 100.00% | 100.00% |
| 2H | 2h | 0 | 1 | 0.00% | 100.00% |
| 2H | 4h | 0 | 1 | 0.00% | 100.00% |
| 2H | 8h | 0 | 1 | 0.00% | 100.00% |
| 2H | 12h | 0 | 1 | 0.00% | 100.00% |
| 2H | 24h | 0 | 1 | 0.00% | 100.00% |
| 2H | 48h | 0 | 1 | 0.00% | 100.00% |

## Censoring evidence

| Clock | Horizon | Missing intervals | Missing runs | Longest missing run | Source-end truncations |
|---|---:|---:|---:|---:|---:|
| 15M | 1h | 719 | 496 | 4 bars | 1 |
| 15M | 2h | 2,111 | 1,196 | 8 bars | 5 |
| 15M | 4h | 6,492 | 2,889 | 16 bars | 10 |
| 15M | 8h | 20,222 | 6,822 | 32 bars | 13 |
| 15M | 12h | 40,881 | 11,187 | 48 bars | 17 |
| 15M | 24h | 119,355 | 17,852 | 96 bars | 21 |
| 15M | 48h | 381,091 | 31,168 | 192 bars | 42 |
| 2H | 1h | 0 | 0 | 0 bars | 0 |
| 2H | 2h | 4 | 1 | 4 bars | 0 |
| 2H | 4h | 12 | 1 | 12 bars | 0 |
| 2H | 8h | 28 | 1 | 28 bars | 0 |
| 2H | 12h | 44 | 1 | 44 bars | 0 |
| 2H | 24h | 92 | 1 | 92 bars | 0 |
| 2H | 48h | 188 | 1 | 188 bars | 0 |

A complete record has every exact 15M interval and an endpoint inside the sealed source. Every other record remains in the dataset with explicit censor evidence; no path was repaired or dropped.

## Gate decision

The neutral outcome engine may now measure only records marked `COMPLETE`. Censored records must receive no return, excursion or path-shape value. Overlap flags must travel with every measured outcome.

The 24h horizon has only **64** complete observations across both clocks and is not broad enough for cohort claims. The 48h horizon has **0** complete observations and is blocked from measurement. This is a sealed-source path-completeness constraint, not a B-STATE classification failure.

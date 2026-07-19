# OVC OPT-C Strict Forward-Path Coverage and Censoring Audit

**Status:** `AUDIT COMPLETE — PARTIAL MEASUREMENT READINESS — 48H BLOCKED`  
**Coverage contract:** `OPT-C-COVERAGE-0.1`  
**Forward price values read:** `NO`

## Coverage by horizon

| Clock | Horizon | Complete | Censored | Complete rate | Overlap rate |
|---|---:|---:|---:|---:|---:|
| 15M | 1h | 3,605 | 240 | 93.76% | 90.40% |
| 15M | 2h | 3,386 | 459 | 88.06% | 96.23% |
| 15M | 4h | 2,984 | 861 | 77.61% | 98.10% |
| 15M | 8h | 2,125 | 1,720 | 55.27% | 99.01% |
| 15M | 12h | 1,282 | 2,563 | 33.34% | 99.35% |
| 15M | 24h | 32 | 3,813 | 0.83% | 99.43% |
| 15M | 48h | 0 | 3,845 | 0.00% | 99.43% |
| 2H | 1h | 416 | 43 | 90.63% | 62.31% |
| 2H | 2h | 390 | 69 | 84.97% | 85.62% |
| 2H | 4h | 338 | 121 | 73.64% | 95.21% |
| 2H | 8h | 261 | 198 | 56.86% | 98.91% |
| 2H | 12h | 192 | 267 | 41.83% | 99.13% |
| 2H | 24h | 4 | 455 | 0.87% | 99.13% |
| 2H | 48h | 0 | 459 | 0.00% | 99.13% |

## Censoring evidence

| Clock | Horizon | Missing intervals | Missing runs | Longest missing run | Source-end truncations |
|---|---:|---:|---:|---:|---:|
| 15M | 1h | 370 | 256 | 4 bars | 0 |
| 15M | 2h | 1,037 | 589 | 8 bars | 0 |
| 15M | 4h | 3,235 | 1,391 | 16 bars | 3 |
| 15M | 8h | 10,106 | 3,185 | 32 bars | 7 |
| 15M | 12h | 19,836 | 5,056 | 48 bars | 13 |
| 15M | 24h | 59,049 | 8,408 | 96 bars | 24 |
| 15M | 48h | 188,930 | 14,930 | 192 bars | 56 |
| 2H | 1h | 70 | 46 | 4 bars | 1 |
| 2H | 2h | 158 | 92 | 8 bars | 1 |
| 2H | 4h | 426 | 198 | 16 bars | 2 |
| 2H | 8h | 1,192 | 366 | 32 bars | 3 |
| 2H | 12h | 2,310 | 507 | 48 bars | 3 |
| 2H | 24h | 7,727 | 941 | 96 bars | 3 |
| 2H | 48h | 28,226 | 1,557 | 192 bars | 3 |

A complete record has every exact 15M interval and an endpoint inside the sealed source. Every other record remains in the dataset with explicit censor evidence; no path was repaired or dropped.

## Gate decision

The neutral outcome engine may now measure only records marked `COMPLETE`. Censored records must receive no return, excursion or path-shape value. Overlap flags must travel with every measured outcome.

The 24h horizon has only **36** complete observations across both clocks and is not broad enough for cohort claims. The 48h horizon has **0** complete observations and is blocked from measurement. This is a sealed-source path-completeness constraint, not a B-STATE classification failure.

# OVC OPT-C Semantic Sanity Review v0.1

**Status:** `PASS WITH OVERLAP AND SPARSE-COHORT CONTROLS`  
**Review contract:** `OPT-C-SEMANTIC-REVIEW-0.1`  
**Edge / trade / execution authority:** `NONE`

## Measurement and nested-horizon integrity

| Clock | Outcome rows | Unique anchors | Arithmetic/semantic violations | Nested-horizon violations |
|---|---:|---:|---:|---:|
| 15M | 13,382 | 3,605 | 0 | 0 |
| 2H | 1,597 | 416 | 0 | 0 |

All return identities, excursion bounds, direction normalization, extreme timing, frontier relations and increasing-horizon invariants passed.

## Overlap concentration

| Clock | Horizon | Rows | Overlapping | Overlap rate |
|---|---:|---:|---:|---:|
| 15M | 1h | 3,605 | 3,328 | 92.32% |
| 15M | 2h | 3,386 | 3,325 | 98.20% |
| 15M | 4h | 2,984 | 2,976 | 99.73% |
| 15M | 8h | 2,125 | 2,125 | 100.00% |
| 15M | 12h | 1,282 | 1,282 | 100.00% |
| 2H | 1h | 416 | 277 | 66.59% |
| 2H | 2h | 390 | 344 | 88.21% |
| 2H | 4h | 338 | 328 | 97.04% |
| 2H | 8h | 261 | 261 | 100.00% |
| 2H | 12h | 192 | 192 | 100.00% |

Overlap is a dominant property of this event ledger, especially at longer horizons. Pooled rows therefore cannot be treated as independent observations. Downstream cohorts must preserve overlap strata and use time-separated or cluster-aware comparison units.

## Frontier applicability

| Clock | Horizon | Directional | Primary frontier | Applicable | Retested | Lost on close |
|---|---:|---:|---:|---:|---:|---:|
| 15M | 1h | 2,992 | 2,987 | 99.83% | 22.93% | 15.40% |
| 15M | 2h | 2,809 | 2,804 | 99.82% | 33.70% | 26.03% |
| 15M | 4h | 2,470 | 2,465 | 99.80% | 47.22% | 40.20% |
| 15M | 8h | 1,732 | 1,727 | 99.71% | 64.33% | 59.18% |
| 15M | 12h | 1,001 | 997 | 99.60% | 67.80% | 63.69% |
| 2H | 1h | 338 | 334 | 98.82% | 6.59% | 4.19% |
| 2H | 2h | 315 | 312 | 99.05% | 10.90% | 7.37% |
| 2H | 4h | 274 | 274 | 100.00% | 18.98% | 13.50% |
| 2H | 8h | 210 | 210 | 100.00% | 31.90% | 27.14% |
| 2H | 12h | 153 | 153 | 100.00% | 40.52% | 33.99% |

## Cohort support gate

The frozen 160-cell clock × horizon × family × direction matrix contains **45** adequate descriptive cells, **29** limited cells, **55** sparse cells and **31** empty cells.

Sparse cells remain inventory-only. Multi-family cells overlap by construction and are not additive.

## Gate decision

The neutral OPT-C measurement semantics pass. The release may advance to an OPT-D cohort-contract draft only if that contract preserves overlap strata, support bands, family membership and the 1–12h complete-path boundary. No pooled independence, threshold optimization, significance, edge or execution claim is authorized.

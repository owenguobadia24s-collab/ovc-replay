# OVC OPT-C Semantic Sanity Review v0.1

**Status:** `PASS WITH OVERLAP AND SPARSE-COHORT CONTROLS`  
**Review contract:** `OPT-C-SEMANTIC-REVIEW-0.1`  
**Edge / trade / execution authority:** `NONE`

## Measurement and nested-horizon integrity

| Clock | Outcome rows | Unique anchors | Arithmetic/semantic violations | Nested-horizon violations |
|---|---:|---:|---:|---:|
| 15M | 26,333 | 7,193 | 0 | 0 |
| 2H | 1 | 1 | 0 | 0 |

All return identities, excursion bounds, direction normalization, extreme timing, frontier relations and increasing-horizon invariants passed.

## Overlap concentration

| Clock | Horizon | Rows | Overlapping | Overlap rate |
|---|---:|---:|---:|---:|
| 15M | 1h | 7,193 | 6,540 | 90.92% |
| 15M | 2h | 6,729 | 6,590 | 97.93% |
| 15M | 4h | 5,925 | 5,914 | 99.81% |
| 15M | 8h | 4,125 | 4,125 | 100.00% |
| 15M | 12h | 2,361 | 2,361 | 100.00% |
| 2H | 1h | 1 | 1 | 100.00% |
| 2H | 2h | 0 | 0 | 0.00% |
| 2H | 4h | 0 | 0 | 0.00% |
| 2H | 8h | 0 | 0 | 0.00% |
| 2H | 12h | 0 | 0 | 0.00% |

Overlap is a dominant property of this event ledger, especially at longer horizons. Pooled rows therefore cannot be treated as independent observations. Downstream cohorts must preserve overlap strata and use time-separated or cluster-aware comparison units.

## Frontier applicability

| Clock | Horizon | Directional | Primary frontier | Applicable | Retested | Lost on close |
|---|---:|---:|---:|---:|---:|---:|
| 15M | 1h | 5,959 | 5,928 | 99.48% | 24.63% | 16.62% |
| 15M | 2h | 5,602 | 5,571 | 99.45% | 36.51% | 28.27% |
| 15M | 4h | 4,946 | 4,916 | 99.39% | 49.61% | 41.68% |
| 15M | 8h | 3,373 | 3,349 | 99.29% | 66.23% | 59.45% |
| 15M | 12h | 1,892 | 1,876 | 99.15% | 69.72% | 64.34% |
| 2H | 1h | 0 | 0 | 0.00% | 0.00% | 0.00% |
| 2H | 2h | 0 | 0 | 0.00% | 0.00% | 0.00% |
| 2H | 4h | 0 | 0 | 0.00% | 0.00% | 0.00% |
| 2H | 8h | 0 | 0 | 0.00% | 0.00% | 0.00% |
| 2H | 12h | 0 | 0 | 0.00% | 0.00% | 0.00% |

## Cohort support gate

The frozen 160-cell clock × horizon × family × direction matrix contains **47** adequate descriptive cells, **6** limited cells, **13** sparse cells and **94** empty cells.

Sparse cells remain inventory-only. Multi-family cells overlap by construction and are not additive.

## Gate decision

The neutral OPT-C measurement semantics pass. The release may advance to an OPT-D cohort-contract draft only if that contract preserves overlap strata, support bands, family membership and the 1–12h complete-path boundary. No pooled independence, threshold optimization, significance, edge or execution claim is authorized.

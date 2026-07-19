# OVC OPT-D Cluster-Aware Cohort Release v0.1

**Status:** `COHORT FORMATION COMPLETE — DESCRIPTIVE ONLY`  
**Contract:** `OPT-D-COHORT-0.1`  
**Edge / trade / execution authority:** `NONE`

## Cross-clock overlap clusters

| Horizon | Outcome rows | Clusters | Median size | Maximum size | Cross-clock clusters |
|---:|---:|---:|---:|---:|---:|
| 1h | 4,021 | 689 | 3.00 | 41 | 193 |
| 2h | 3,776 | 301 | 6.00 | 53 | 109 |
| 4h | 3,322 | 156 | 24.00 | 76 | 79 |
| 8h | 2,386 | 123 | 20.00 | 68 | 77 |
| 12h | 1,474 | 117 | 13.00 | 59 | 68 |

Clusters are connected components of half-open forward windows across both event clocks. They prevent overlapping 15M and 2H anchors from being presented as separate support. Cluster count is still not an independence claim.

## Base-cohort readiness

| Readiness | Cohorts |
|---|---:|
| `DESCRIPTIVE_COHORT_READY` | 30 |
| `EMPTY` | 31 |
| `INVENTORY_ONLY_CLUSTER_SPARSE` | 4 |
| `INVENTORY_ONLY_ROW_SPARSE` | 55 |
| `LIMITED_CLUSTERED_DESCRIPTION` | 40 |

## Exact-signature readiness

| Readiness | Cohorts |
|---|---:|
| `DESCRIPTIVE_COHORT_READY` | 15 |
| `INVENTORY_ONLY_CLUSTER_SPARSE` | 9 |
| `INVENTORY_ONLY_ROW_SPARSE` | 1,192 |
| `LIMITED_CLUSTERED_DESCRIPTION` | 70 |

Exact semantic signatures use the set of family/subtype/direction components. Level IDs do not fragment the vocabulary; multi-family base memberships remain explicit and non-additive.

## Gate decision

The cohort formation layer is complete. Only cohorts labelled `DESCRIPTIVE_COHORT_READY` may enter the first repeated-story comparison design; limited cohorts remain labelled, and all inventory-only cohorts are prohibited from comparison. The next gate must freeze contrast construction, counterexample retention and temporal validation without treating clusters as statistically independent.

# OVC OPT-D Cluster-Aware Cohort Release v0.1

**Status:** `COHORT FORMATION COMPLETE — DESCRIPTIVE ONLY`  
**Contract:** `OPT-D-COHORT-0.1`  
**Edge / trade / execution authority:** `NONE`

## Cross-clock overlap clusters

| Horizon | Outcome rows | Clusters | Median size | Maximum size | Cross-clock clusters |
|---:|---:|---:|---:|---:|---:|
| 1h | 7,194 | 1,173 | 4.00 | 42 | 1 |
| 2h | 6,729 | 409 | 16.00 | 43 | 0 |
| 4h | 5,925 | 271 | 23.00 | 60 | 0 |
| 8h | 4,125 | 251 | 17.00 | 48 | 0 |
| 12h | 2,361 | 207 | 11.00 | 40 | 0 |

Clusters are connected components of half-open forward windows across both event clocks. They prevent overlapping 15M and 2H anchors from being presented as separate support. Cluster count is still not an independence claim.

## Base-cohort readiness

| Readiness | Cohorts |
|---|---:|
| `DESCRIPTIVE_COHORT_READY` | 44 |
| `EMPTY` | 94 |
| `INVENTORY_ONLY_CLUSTER_SPARSE` | 2 |
| `INVENTORY_ONLY_ROW_SPARSE` | 13 |
| `LIMITED_CLUSTERED_DESCRIPTION` | 7 |

## Exact-signature readiness

| Readiness | Cohorts |
|---|---:|
| `DESCRIPTIVE_COHORT_READY` | 49 |
| `INVENTORY_ONLY_CLUSTER_SPARSE` | 6 |
| `INVENTORY_ONLY_ROW_SPARSE` | 1,067 |
| `LIMITED_CLUSTERED_DESCRIPTION` | 74 |

Exact semantic signatures use the set of family/subtype/direction components. Level IDs do not fragment the vocabulary; multi-family base memberships remain explicit and non-additive.

## Gate decision

The cohort formation layer is complete. Only cohorts labelled `DESCRIPTIVE_COHORT_READY` may enter the first repeated-story comparison design; limited cohorts remain labelled, and all inventory-only cohorts are prohibited from comparison. The next gate must freeze contrast construction, counterexample retention and temporal validation without treating clusters as statistically independent.

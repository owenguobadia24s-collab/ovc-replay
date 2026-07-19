# OVC OPT-D Cluster-Aware Cohort Contract v0.1

**Contract ID:** `OPT-D-COHORT-0.1`  
**Parent:** `OPT-C-SEMANTIC-REVIEW-0.1`  
**Status:** `RATIFIED FOR DESCRIPTIVE COHORT FORMATION`

## Unit of evidence

The source outcome row remains immutable. OPT-D adds an overlap-cluster identity
without merging, averaging or selecting a representative outcome.

For each horizon separately, all 15M and 2H event windows are sorted together.
Each window is half-open: `[anchor_time, endpoint_time)`. Windows belong to the
same cluster when they overlap directly or through a transitive chain. An anchor
starting exactly when the prior cluster ends begins a new cluster.

Clusters are cross-clock because all outcomes use the same sealed 15M forward
path. Cluster count is de-duplicated descriptive support, not proof of
independence or effective sample size.

## Cohort layers

1. **Base cohorts:** event clock × horizon × event family × event direction.
   Multi-family events enter every applicable family cohort; cells are not
   additive.
2. **Exact semantic-signature cohorts:** event clock × horizon × the sorted set
   of `(family, subtype, direction)` components. Level IDs and source-record IDs
   do not alter the signature.

Every membership binds one outcome record, event anchor, overlap cluster and
cohort ID.

## Support controls

Raw rows and distinct overlap clusters are banded separately:

| Count | Band |
|---:|---|
| 0 | `EMPTY` |
| 1–29 | `SPARSE` |
| 30–99 | `LIMITED` |
| 100+ | `ADEQUATE` |

Cohort readiness is conservative:

- any row count below 30: `INVENTORY_ONLY_ROW_SPARSE`;
- any cluster count below 30: `INVENTORY_ONLY_CLUSTER_SPARSE`;
- fewer than three represented months: `INVENTORY_ONLY_TEMPORALLY_NARROW`;
- either row or cluster count below 100: `LIMITED_CLUSTERED_DESCRIPTION`;
- otherwise: `DESCRIPTIVE_COHORT_READY`.

These labels authorize description only. Connected clusters can still be
serially dependent.

## Prohibitions

This contract cannot choose thresholds, pool sparse cells, infer statistical
independence, calculate significance, call a result a win/loss, establish edge,
recommend action, size risk or authorize trading/production/execution.

The 24h horizon remains coverage-only and 48h remains blocked.

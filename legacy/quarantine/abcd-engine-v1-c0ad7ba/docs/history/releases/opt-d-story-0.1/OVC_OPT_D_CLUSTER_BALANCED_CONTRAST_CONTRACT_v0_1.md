# OVC OPT-D Cluster-Balanced Contrast Contract v0.1

**Contract ID:** `OPT-D-CONTRAST-0.1`  
**Parent:** `OPT-D-COHORT-0.1`  
**Status:** `RATIFIED FOR DESCRIPTIVE CONTRAST CONSTRUCTION`

## Exhaustive templates

Contrasts are generated without outcome-based selection:

1. **Base direction symmetry:** `UP` versus `DOWN` for every event clock,
   horizon and family where both base cohorts are descriptive-ready.
2. **Base family context:** every pair of descriptive-ready families sharing
   event clock, horizon and event direction.
3. **Exact signature context:** every pair of descriptive-ready exact semantic
   signatures sharing event clock, horizon and event direction.

Family-context arms exclude outcomes belonging to both families. Those shared
outcomes are retained as a separate evidence stratum and cannot enter either
exclusive arm. Direction and exact-signature arms are mutually exclusive by
outcome, but overlapping clusters remain explicit.

## Cluster-balanced description

Each arm is grouped by the ratified cross-clock overlap-cluster ID. The metric
is first reduced to a median inside each cluster, then summarized across cluster
medians. This gives each represented cluster equal descriptive mass regardless
of event density. It does not establish independence or effective sample size.

The primary metric is direction-normalized endpoint return for directional
arms and raw endpoint return for `MIXED`/`NONE` arms. No metric may be selected
after seeing its contrast value.

## Counterexample retention

Every arm materializes:

- `OPPOSITE_DIRECTION_ENDPOINT` when a directional normalized endpoint return
  is below zero;
- `PRIMARY_FRONTIER_LOSS_ON_CLOSE` when the corresponding field is true.

Counterexamples remain linked to outcome, event anchor, overlap cluster,
contrast and arm. They cannot be dropped, winsorized or relabelled as trades.

## Temporal stability

The same cluster-balanced metric is recomputed by anchor month. A month enters
the contrast delta only when both arms contain at least five represented
clusters. Fewer than three eligible months is insufficient. Otherwise the
release reports only whether at least 80% of eligible monthly deltas share one
sign or whether signs are mixed. No significance or probability is inferred.

## Readiness

After family exclusivity:

- either arm below 30 rows or clusters: `INVENTORY_ONLY_AFTER_EXCLUSIVITY`;
- either arm below three months: `INVENTORY_ONLY_TEMPORALLY_NARROW`;
- either arm below 100 rows or clusters: `LIMITED_CLUSTERED_CONTRAST`;
- otherwise: `DESCRIPTIVE_CONTRAST_READY`.

## Prohibitions

This release cannot pool sparse arms, optimize thresholds, infer independence,
run significance tests, claim conditional probability or edge, recommend
action, size risk, or authorize trading, production or execution. The 24h
horizon remains coverage-only and 48h remains blocked.

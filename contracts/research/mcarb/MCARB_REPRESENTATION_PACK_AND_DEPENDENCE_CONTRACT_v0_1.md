# MCARB Representation Pack and Dependence Contract v0.1

Representation packs are explicit, hash-addressable research views. Pack identity binds exact field IDs,
variant IDs, normalization IDs, comparability domain, time basis, missingness policy and complexity declaration.
No pack name implies hidden fields.

Frozen pack IDs:
- `R0 = PRICE`
- `R1 = PRICE + AL`
- `R2 = PRICE + ET`
- `R3 = PRICE + VS`
- `R4 = PRICE + AL + VS`
- `R4X = PRICE + AL + ET`
- `R5 = PRICE + ET + VS`
- `R6 = PRICE + AL + ET + VS`
- `D-AL`, `D-ET`, `D-VS` are diagnostic-only auxiliary packs.

R6 SHALL expose an R4X nested-ablation comparison. Auxiliary-only packs cannot masquerade as structural models.

Dependence evidence is descriptive and grouped by an explicit comparability domain. Allowed initial methods are
Pearson correlation and deterministic rank correlation for numeric fields; mutual information is `DISABLED_UNTIL_PREREGISTERED`.
Required controls are nested ablation, clock-slot/side/missingness-preserving shuffle controls and matched-complexity
noise/dimensionality controls. A dependence result cannot select a scientific winner or promote a pack.

Complexity declarations include at minimum: feature count, free parameter count, lookback burden, missingness burden,
categorical cardinality, and optional effective-information estimate. `null` is permitted when a metric is not yet evaluable;
hidden defaults are not.

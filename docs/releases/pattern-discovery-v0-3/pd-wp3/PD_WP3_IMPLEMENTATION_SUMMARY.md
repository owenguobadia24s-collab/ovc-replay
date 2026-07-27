# PD-WP3 — Deterministic Fingerprints and Provisional Clustering

## Status

`QA_REVIEW_PD_G3`

## Governing plan

- Plan: `OVC C2 Pattern Discovery and Review Layer v0.3`
- Source SHA-256: `03a4c602026950f3a496f6bf2085c378a62292090d334f3b0ea2f17f6463a0aa`
- Approved prerequisite: `PD-G2 PASS`
- Baseline main commit: `ff9f8a9604d352bb37777e04282cd0641e5f38b8`
- Branch: `build/pd-wp3-fingerprint-clustering`
- Pull request: `#94`

## Implemented capability

- deterministic completed-window PatternFingerprint identity;
- five-axis initial/terminal state, occupancy and persistence representation;
- ordered transition, interaction, cross-scale, duration and quality domains;
- recursive prohibited outcome/semantic feature denial;
- frozen six-domain composite distance;
- median/IQR ScalePack with clipping and explicit missingness penalties;
- hard structural partitioning;
- exact deterministic PAM BUILD/SWAP;
- penalized-silhouette k selection and frozen tie-breakers;
- `UNASSIGNED_SMALL_SAMPLE` for partitions below five;
- `CLUSTER_BUILD_CAPACITY_BLOCK` above 500;
- immutable provisional ClusterVersions, medoids, assignments, dispersion and outliers;
- explicit cluster-lineage mapping;
- arrival-order, tie, medoid-displacement, mixed-version and capacity fixtures.

## Authority boundary

All outputs are derived research representations. Machine clusters remain provisional and cannot create semantic names, archetypes, C2E episodes, C3 meanings, active novelty ranking, evidence writes, selectors, releases, R2, Validation, probability, exposure, trading, execution or agent authority.

## QA position

Initial focused, retained and canonical workflows passed on the first implementation candidate. Final candidate workflow IDs and hashes are recorded in the QA packet after the complete gate state is materialized.

## Rollback

Delete and rebuild fingerprints, distance matrices, assignments and ClusterVersions from accepted candidate sources. Historical decision records remain immutable; canonical C2 and accepted PD-WP1/PD-WP2 authority remain unchanged.

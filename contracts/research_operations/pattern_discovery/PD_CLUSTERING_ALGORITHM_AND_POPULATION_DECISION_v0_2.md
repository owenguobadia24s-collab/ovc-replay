# PD Clustering Algorithm and Population Decision v0.2

## Decision

Use deterministic two-stage clustering:

1. Hard structural partitioning.
2. Exact Partitioning Around Medoids (PAM) inside each eligible partition.

PAM is selected because its representative is an actual candidate, it accepts non-Euclidean composite distance, and it is explainable through medoid/member comparisons. K-means is rejected because categorical paths and missingness do not admit a meaningful centroid. Incremental pinned-medoid methods are rejected because early cases may dominate later structure.

## Structural partition

A candidate is partitioned by:

- clock and price side;
- primary transition grammar;
- boundary-interaction class;
- parent-containment class;
- closure class.

Different partitions never compete in one PAM build.

## Composite distance

`D_total = 0.25 D_state_path + 0.25 D_transition_sequence + 0.15 D_interaction + 0.15 D_cross_scale + 0.10 D_duration_persistence + 0.10 D_quality`

Domain methods:

- categorical initial/state features: weighted Gower/Hamming;
- ordered transition sequence: normalized Levenshtein;
- relation and trigger sets: Jaccard;
- occupancy, duration and persistence: robust-scaled Manhattan;
- quality and missingness: weighted categorical plus numeric distance.

Numerical scaling uses the calibration-set median and interquartile range with registry-declared clipping. Every feature, weight, mapping, clipping rule and missingness penalty is versioned.

## Missingness

- Both available: compute domain distance.
- Both absent for the same explicit reason: zero or the registry-declared small distance.
- One unavailable: apply the declared missingness penalty.
- Both unavailable for different reasons: apply the larger penalty.
- Renormalize evaluated-domain weights while retaining an explicit missingness contribution.

Missing is never silently treated as equal or neutral.

## k selection

For partition size `n >= 5`, evaluate `k = 1..min(8, floor(sqrt(n)))`.

Select the best penalized silhouette result. Ties resolve in order:

1. lower `k`;
2. lower total within-cluster distance;
3. lexicographically smaller ordered medoid-ID set.

`n < 5` yields `UNASSIGNED_SMALL_SAMPLE`.

## Rebuild policy

Operational builds use the complete eligible active set within the frozen capacity bound. Medoids are not pinned. Each rebuild creates an immutable ClusterVersion and maps previous clusters as retained, split, merged, dissolved or unmatched.

Historical audit may use the complete retained valid population offline. No historical ClusterVersion is mutated.

## Eligible clustering population

Include:

- valid deterministically closed triggered candidates;
- otherwise-valid candidates suppressed only by queue caps;
- matched and population controls;
- dismissed candidates with disposition metadata.

Exclude:

- invalid, quarantined or unresolved-lineage candidates;
- fingerprint failures;
- mixed fingerprint versions;
- `TIME_GATED_REPLAY` and `NON_EVIDENTIARY_REPLAY` outputs from prospective counts;
- any candidate containing a prohibited outcome feature.

## Cluster status

Machine output may be `PROVISIONAL`, `RECURRING`, `REVIEW_REQUIRED`, `RESTRICTED`, `REJECTED` or `SUPERSEDED`. `ARCHETYPE_PROPOSAL` is human-authored proposal status only. No cluster status grants C2E or C3 authority.

## Required stability fixtures

PD-WP3 must demonstrate:

- identical inputs produce identical medoids and memberships;
- arrival-order permutations do not change a batch rebuild;
- near-tie silhouette cases obey the frozen tie-breaker;
- adding a better representative may displace an early medoid;
- mixed fingerprint versions fail closed;
- partitions over the capacity bound produce `CLUSTER_BUILD_CAPACITY_BLOCK`, not an approximate fallback.
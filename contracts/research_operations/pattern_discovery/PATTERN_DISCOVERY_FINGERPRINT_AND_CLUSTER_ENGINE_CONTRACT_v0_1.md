# Pattern Discovery Fingerprint and Cluster Engine Contract v0.1

## Packet and authority

This contract governs `PD-WP3` under approved `PD-G2` derived trigger, control and novelty-shadow authority.

The packet may build deterministic completed-candidate PatternFingerprints, calculate the frozen composite distance, partition eligible candidates, perform exact deterministic PAM, create immutable provisional ClusterVersions, identify medoids and outliers, and map cluster lineage between versions.

It may not activate live processing, active novelty ranking, semantic names, archetypes, C2E episodes, C3 meaning, evidence writes, selectors, releases, R2, Validation, outcomes, probability, exposure, trading, execution or agent authority.

## Fingerprint identity

A completed fingerprint binds:

- candidate-window ID and exact source release lineage;
- clock, side, scope and deterministic window bounds;
- fingerprint version;
- initial five-axis state;
- ordered state and transition paths;
- axis occupancy and persistence;
- interaction and relation events;
- cross-scale context;
- duration and switching measures;
- quality, missingness and censoring;
- trigger IDs and control class;
- hard structural partition fields.

The fingerprint excludes local paths, run timestamps, machine IDs, returns, MFE, MAE, outcomes, profitable direction, trade labels and semantic archetype names.

Fingerprint identity is canonical SHA-256 over the complete versioned payload.

## Composite distance

The implementation follows `PD_CLUSTERING_ALGORITHM_AND_POPULATION_DECISION_v0_2.md`:

`D_total = 0.25 D_state_path + 0.25 D_transition_sequence + 0.15 D_interaction + 0.15 D_cross_scale + 0.10 D_duration_persistence + 0.10 D_quality`

- state path: categorical Hamming/Gower plus occupancy difference;
- ordered transitions: normalized Levenshtein;
- interaction/relation sets: Jaccard;
- cross-scale context: weighted categorical distance;
- duration/persistence: median/IQR robust-scaled Manhattan with clipping;
- quality/missingness: categorical plus numeric distance and explicit penalties.

All weights, clipping, penalties, feature maps and scale statistics are recorded in the DistancePack and ScalePack. Missingness is never treated as neutral silently.

## Eligible population

Include valid deterministically closed triggered candidates, otherwise-valid queue-suppressed candidates, matched and population controls, and dismissed candidates with disposition metadata.

Exclude invalid, quarantined, unresolved-lineage or fingerprint-failed candidates; mixed fingerprint versions; non-evidentiary replay outputs from prospective counts; and any candidate with prohibited outcome fields.

## Structural partition

The hard partition key is:

- clock;
- price side;
- primary transition grammar;
- boundary-interaction class;
- parent-containment class;
- closure class.

Different partitions never compete in one PAM build.

## Exact deterministic PAM

For every partition with `n >= 5`, evaluate `k = 1..min(8, floor(sqrt(n)))`.

PAM uses deterministic BUILD and SWAP phases. All candidates are sorted by fingerprint ID before computation. Assignment ties resolve to the lexicographically smaller medoid ID. Model-selection ties resolve by:

1. lower `k`;
2. lower total within-cluster distance;
3. lexicographically smaller ordered medoid-ID set.

Penalized silhouette is the mean silhouette less the versioned complexity penalty. `n < 5` returns `UNASSIGNED_SMALL_SAMPLE`.

## Capacity and failure

The operational active set is capped at 500 candidates per structural partition. A larger set returns `CLUSTER_BUILD_CAPACITY_BLOCK`. No approximate or silent sampling fallback is permitted.

Mixed fingerprint versions, duplicate fingerprint IDs, missing partition fields, prohibited outcome features or non-finite distance values fail closed.

## ClusterVersion

Every immutable ClusterVersion binds:

- exact input-candidate-set hash;
- fingerprint, distance, scale and algorithm versions;
- structural partition;
- selected k and model-selection metrics;
- medoid IDs;
- member assignments and distances;
- dispersion and outlier thresholds;
- temporal and clock coverage;
- previous-version lineage where supplied.

Machine-generated status is `PROVISIONAL`, `RECURRING`, `REVIEW_REQUIRED`, `RESTRICTED`, `REJECTED` or `SUPERSEDED`. `ARCHETYPE_PROPOSAL` is forbidden to machine output.

## PD-G3 acceptance

PD-G3 may pass only if:

1. identical inputs produce identical fingerprints, distances, medoids and memberships;
2. arrival-order permutations do not change a batch result;
3. the frozen tie-breakers are demonstrated;
4. an added better representative may displace an earlier medoid;
5. mixed versions fail closed;
6. partitions over 500 produce `CLUSTER_BUILD_CAPACITY_BLOCK`;
7. `n < 5` produces `UNASSIGNED_SMALL_SAMPLE`;
8. no outcome or semantic authority is present;
9. focused, retained-boundary and canonical repository tests pass.

## Rollback

Delete and rebuild fingerprints, distance matrices, assignments and cluster versions from accepted candidate sources. Historical ClusterVersions and decision records remain immutable. Canonical C2, selectors, releases, evidence and R2 remain unchanged.

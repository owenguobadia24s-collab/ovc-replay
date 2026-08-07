# MG C2G Sensitivity and Hierarchy Contract v0.1

**Contract ID:** `MG-C2G-SENSITIVITY-HIERARCHY-0.1`  
**Programme:** `OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1`  
**Packet:** `MG-WP3`  
**Authority:** inactive, noncanonical `SHADOW_EXPERIMENT` computation only

## 1. Purpose

Build deterministic comparison families across versioned sensitivity packs and a cross-pack
hierarchy without declaring any sensitivity, family or hierarchy canonical. A family is a
sensitivity-dependent research object represented by a real medoid and exact member set,
not a promoted market type.

## 2. Input boundary

C2G-S consumes typed `STATE`, `TRANSITION` or `EPISODE` records whose distance vector is
explicitly `STRUCTURAL`. Context and provenance remain identity/applicability metadata and
never enter the structural vector.

Forbidden construction inputs include source/provenance fields inside the structural
feature vector, computability fields as structural features, future path, outcome, return,
MFE/MAE, semantic labels, grammar/parse identities, probability, risk, exposure and
execution.

`NOT_EVALUABLE` records remain explicit and cannot be converted to a neutral vector.

## 3. Sensitivity packs

Each pack freezes:

- `WEIGHTED_MANHATTAN_V0_1`;
- the structural feature allowlist and weights;
- missingness policy `NOT_EVALUABLE`;
- assignment radius and ambiguity margin;
- minimum support;
- a declared but WP4-unconsumed variant radius;
- containment and partial-overlap thresholds;
- deterministic tie-break `MAX_COVERAGE_MIN_TOTAL_DISTANCE_LEXICOGRAPHIC_ID`.

The comparison registry contains `0.20`, `0.25`, `0.35`, `0.40` and `0.50`. No pack has
`canonical=true`; none is an active selector or threshold authority.

## 4. Deterministic family construction

Within each exact `(release, instrument, side, scope, clock, record_type)` partition:

1. sort records by first-valid time and record identity;
2. exclude explicit or feature-incomplete records as `NOT_EVALUABLE`;
3. compute pairwise weighted Manhattan distances using `Decimal`;
4. choose the real medoid candidate that maximises remaining coverage within the pack
   radius, then minimises total covered distance, then uses lexicographic `record_id`;
5. materialise the covered star only if support is at least the pack minimum;
6. remove covered members and repeat;
7. leave unsupported remainder `UNASSIGNED`.

Every family records the exact member IDs, real medoid ID and mean member-to-medoid
dispersion. IDs are hashes of canonical, environment-independent payloads.

## 5. Assignment ledger

Every input becomes exactly one of:

- `ASSIGNED`
- `AMBIGUOUS`
- `UNASSIGNED`
- `NOT_EVALUABLE`

`RESIDUAL` is reserved for MG-WP4 and is not emitted by MG-WP3.

Assignments retain all medoid candidate distances. `AMBIGUOUS` requires a second family
within the frozen ambiguity margin of the nearest family. Missingness is never neutrality.

## 6. Hierarchy

Only adjacent sensitivity results over the identical input population and cutoff are
compared. The higher-radius family is the possible parent and the lower-radius family the
possible child.

- `PARENT_OF`: overlap containment meets the frozen containment threshold.
- `PARTIAL_OVERLAP_WITH`: containment fails but Jaccard overlap meets the frozen
  partial-overlap threshold. This relation is non-directional and excluded from cycle
  checks.

Directional edges must strictly descend in sensitivity and therefore form an acyclic DAG.
The ledger records Jaccard overlap, containment, medoid persistence, split events, merge
events, family survival and adjacent-pack reassignment rate.

## 7. Determinism and chronology

- input iteration order cannot affect families, assignments, edges or IDs;
- first-valid timestamps are normalised to UTC and records after `build_cutoff` are
  rejected;
- machine, path, process and run-time labels are unsupported inputs;
- no downstream record may rewrite C2 or C2E history.

## 8. Authority

This packet creates only inactive comparison objects. It does not authorise:

- a canonical sensitivity pack, family, medoid, hierarchy or variant;
- family or theory promotion;
- selector activation or replacement;
- C2/C2E mutation;
- C2P grammar promotion or C3 handoff;
- publication or Validation consumption;
- probability, risk, exposure or execution.

## 9. Acceptance

MG-WP3 passes only when:

- all frozen packs are explicitly noncanonical;
- structural contamination and future/outcome inputs fail closed;
- same inputs under any iteration order yield identical result bytes;
- every medoid is a real member;
- explicit missingness yields `NOT_EVALUABLE`;
- directional hierarchy edges descend sensitivity and are acyclic;
- split/merge/overlap/persistence/dispersion/survival/reassignment evidence is explicit;
- focused and complete repository tests, FINAL_HEAD, compatibility and merge readiness
  pass with zero unresolved review threads;
- QA records zero reserved authority delta.

## 10. Rollback

Remove or supersede the inactive C2G-S/C2G-H implementation while preserving contracts,
packs, fixtures, QA, decisions and negative evidence. Never promote a pack to repair a
failed comparison and never rewrite C2/C2E history.

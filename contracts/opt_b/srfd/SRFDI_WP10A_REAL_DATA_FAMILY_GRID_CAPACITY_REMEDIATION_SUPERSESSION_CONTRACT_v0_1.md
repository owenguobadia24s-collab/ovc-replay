# SRFDI-WP10A Real-Data Family-Grid Capacity-Remediation Supersession Contract v0.1

## 0. Identity and status

- **Programme:** OVC-SRFD-BENCHMARK-v0.1
- **Parent plan:** OVC-SRFD-IMPLEMENTATION-PLAN-0.1
- **Preparation packet:** SRFDI-WP10A-PREPARATION
- **Operator gate:** SRFDI-G10A
- **Proposed execution packet after approval:** SRFDI-WP10A
- **Proposed next operator stop:** SRFDI-G10A-FREEZE
- **Preparation baseline:** main @ `1b5cea7d01f83706e34c7f041aa5662657e1b4d7`
- **Triggering blocker evidence:** PR #433 @ `f9bbeba065cf85f5a5f5c0a88e9c9d0ea6fa96d7`
- **Status:** PROPOSED / GATE-READY / NO AUTHORITY EFFECT

This contract prepares a bounded implementation-only supersession of the failed
`SRFDI-WP10-v0.4` execution route. It does not itself authorize remediation,
market execution, a new June run, a method/family decision, publication,
Validation use, selector mutation, probability, risk, exposure or execution.

## 1. Court-record reconciliation

Current `main` still points at
`registries/implementation/srfd/OVC_SRFDI_STATE_v0_12.json` and records the
v0.4 token as **unconsumed**. PR #433 deliberately remains open and unmerged
and records the actual post-start capacity blocker with the same v0.4 token as
**consumed / not reusable**.

This is an explicit court-record divergence, not a fact to silently reconcile.

`SRFDI-G10A SUPERSEDE`, if approved, must do two things in order:

1. admit and preserve the exact PR #433 blocker evidence by pinned head/content
   identity, recording the consumed token without rewriting history; and
2. supersede only the failed WP10-v0.4 **execution implementation route** with
   bounded WP10A capacity-remediation authority.

The v0.4 scientific preregistration and its source/population semantics are not
superseded by this packet.

## 2. Triggering evidence

The exact blocker is
`CAPACITY_UNRESOLVED_REAL_DATA_FULL_GRID`.

Preserved evidence from PR #433 states:

- source C2 records: **9,420**
- frozen eligible population: **8,598**
- context records: **822**
- exclusions: **0**
- EVALUABLE / NOT_EVALUATED: **4,996 / 3,602**
- comparability domains: **36**
- exact pair opportunities: **35,380,668**
- frozen family configuration instances: **1,944**
- real-data probe domain: **1,249 records / 779,376 pairs**
- medoid-star required anchor: **1.7595274448394775 s**
- complete-linkage required anchor: **8.275994062423706 s**
- average-linkage anchor: **did not complete inside 240 s**
- resulting capacity status: **CAPACITY_UNRESOLVED**

The 240-second process window is a capacity signal only. It is not a scientific
method comparison and it is not a claim that the inherited T0 wall limit of
14,400 seconds had already been exceeded.

## 3. Frozen scientific invariants

WP10A may change **how** the family grid is computed. It may not change **what**
the frozen benchmark asks to compute.

The following remain immutable inputs:

- preregistration:
  `OVC-SRFD-JUNE-PREREG-v0.4-CANDIDATE`
  / logical SHA-256
  `f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3`
- representation-pack registry logical SHA-256:
  `7d93994836bfcff6c5a0b39db33692f70b1a25782bee43c7b6329d17568561c0`
- segmentation registry logical SHA-256:
  `6c2451fb5b766d2ae25a13a311ba17c8dede342757d607219e62881be4ac31c0`
- stability metric registry logical SHA-256:
  `371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b`
- source binding SHA-256:
  `4d13c3ee8ae2ad25e30088f4f2de48f8320e3633c2e4ea6a5c2c9a7fdc2a62b7`
- population ID:
  `SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd`
- eligible record count / ID hash:
  `8598` /
  `fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e`
- 36 comparability domains
- all 1,944 frozen family configuration instances
- family methods:
  `GREEDY_LEXICOGRAPHIC_MEDOID_STAR`,
  `COMPLETE_LINKAGE`,
  `AVERAGE_LINKAGE`,
  `BOUNDED_PAM`
- all frozen radii, minimum-support values, k values, assignment radii and
  iteration limits
- lexicographic stable tie policy
- residual/noise/singleton visibility
- no full-assignment target
- no scientific promotion

A performance optimization that cannot reproduce the frozen logical result
leaves WP10A and returns to scientific governance.

## 4. Exact grid structure

The frozen family grid is not 1,944 unrelated scientific hypotheses. It is the
exact Cartesian materialization of the frozen method/parameter ladders over 36
comparability domains.

Per domain, 54 configuration instances are required:

- medoid-star: 3 radii × 3 minimum-support values = 9
- complete linkage: 3 radii × 3 minimum-support values = 9
- average linkage: 3 radii × 3 minimum-support values = 9
- bounded PAM: 3 k values × 3 assignment radii × 1 max-iteration value ×
  3 minimum-support values = 27

`36 × 54 = 1,944`.

WP10A may exploit exact shared computation, but every one of the 1,944
configuration identities must remain separately materialized/addressable and
must retain the same logical output it would receive from an independent
reference execution.

## 5. Proposed implementation-only remediation

### 5.1 Reference oracle remains authoritative

`src/ovc/opt_b/srfd/families.py` remains the semantic oracle.

Existing optimized code may be replaced or supplemented only behind versioned
implementation identities. Exact catalog output, family IDs, member sets,
residuals, singleton/noise state, ordering and logical hashes remain the
equivalence target.

### 5.2 Exact average-linkage sum/count backend

The current optimized average-linkage path recomputes every base member-pair
distance for each newly merged cluster. WP10A may implement
`AVERAGE_LINKAGE_EXACT_SUM_COUNT_HEAP` with the following invariants:

- for each live cluster pair, retain the exact sum of finite `Decimal` base
  distances and the integer pair count;
- on merge `(A,B) -> AB`, derive
  `sum(AB,C) = sum(A,C) + sum(B,C)` and
  `count(AB,C) = count(A,C) + count(B,C)`;
- compare candidate average distances by exact cross multiplication rather
  than recursively averaging rounded means;
- compare the radius threshold by exact `sum <= radius * count`;
- preserve the frozen merged-cluster lexicographic tie rule;
- never use float arithmetic in the scientific decision path;
- retain deterministic checkpoint/restart identity.

A different backend is admissible only if it proves the same exact properties.

### 5.3 Exact hierarchical trace reuse

For complete and average linkage, radius and minimum support do not alter the
underlying ordered agglomeration trace before the radius stop. WP10A may compute
one exact linkage trace per domain/linkage method and materialize the frozen
radius/minimum-support catalogs from that trace.

Required proof:

- each of the nine complete-linkage configurations per domain equals an
  independent reference result;
- each of the nine average-linkage configurations per domain equals an
  independent reference result;
- no post-result radius or support selection occurs.

### 5.4 Exact medoid-star radius-path reuse

For a fixed radius, minimum support changes the lawful stopping point but not
the earlier greedy selections. WP10A may compute the minimum-support-2 path and
materialize support-4/support-8 outputs by exact verified prefix termination and
residual reconstruction.

This reuse is admitted only after exhaustive equivalence tests across golden,
adversarial and representative real-data capacity-only domains.

### 5.5 Exact bounded-PAM minimum-support reuse

In the frozen current implementation, `minimum_support` affects final family
versus residual materialization after the PAM iteration path; it does not alter
assignment/update iteration.

WP10A may therefore compute one exact run per
`(k, max_assignment_distance, max_iterations)` combination and materialize the
three minimum-support variants only if exact equality to independent reference
runs is demonstrated.

### 5.6 No promised speedup

The potential reduction in heavy kernel executions is an engineering
hypothesis, not a gate fact. No claimed speedup is accepted before measurement.

## 6. Real-data capacity-only authority proposed

If and only if `SRFDI-G10A = SUPERSEDE`, WP10A may use the frozen real June
population for **capacity-only** family-grid engineering.

Lawful inputs are limited to:

1. already-produced, hash-verifiable representation/distance capacity artifacts
   from the consumed v0.4 attempt; or
2. deterministic reconstruction of the same representation/distance capacity
   inputs from the already accepted local source binding when the preserved
   artifact is unavailable.

No provider fetch is allowed.

Any family catalogs generated during WP10A are
`CAPACITY_ONLY_NON_SCIENTIFIC`. Their memberships, apparent structure,
cross-method behavior or stability may not be used to choose a backend,
representation, method, parameter or future scientific disposition.

Segmentation, stability metrics, G10 scientific disposition and WP11 are
outside WP10A.

## 7. Capacity contract

Inherited T0 remains the only admitted execution envelope:

- max wall: **14,400 s**
- max peak RSS: **17,179,869,184 bytes**
- max new external artifacts: **10,737,418,240 bytes**
- silent sampling: **forbidden**
- silent method/configuration removal: **forbidden**
- approximation: **forbidden unless already a frozen benchmark method**
- cache/parallel credit: only when explicitly measured and identity-safe

Terminal capacity outcomes:

- `PASS_FULL_GRID_T0`
- `CAPACITY_EXCEEDED`
- `REDESIGN_REQUIRED`
- `EQUIVALENCE_FAILURE`
- `ARTIFACT_UNAVAILABLE`
- `BLOCKED_DEPENDENCY`

Capacity status has no scientific meaning.

## 8. Required equivalence programme

Before real-data capacity evidence can support a freeze recommendation, WP10A
must prove:

- reference versus optimized catalog equality;
- family ID equality;
- member/residual/noise/singleton equality;
- tie/path equality;
- worker-count/order equality;
- cold/restart equality;
- checkpoint logical equality;
- materialized-grid equality to independent per-configuration execution;
- exact failure semantics on missing/corrupt distance state;
- no use of scientific outcome values for backend selection.

Any mismatch is a blocking failure.

## 9. Required artifacts after approval

WP10A must produce, at minimum:

- implementation pack/registry with immutable backend identities;
- blocker-admission/supersession receipt for exact PR #433 evidence;
- average-linkage exactness receipt;
- grid-materialization equivalence receipt;
- golden/adversarial equivalence packet;
- real-data capacity-only manifest;
- full-grid T0 capacity receipt;
- restart/determinism receipt;
- external-artifact hash manifest;
- QA packet;
- `SRFDI-G10A-FREEZE` operator packet;
- candidate programme state.

Bulky representation, pair, cache and family payloads remain outside Git.

## 10. Authority boundaries

### Allowed only after SRFDI-G10A SUPERSEDE

- bounded implementation changes described above;
- synthetic/golden/adversarial equivalence tests;
- exact real-data capacity-only family-grid execution against the frozen
  v0.4 population;
- compact evidence and operator packet creation.

### Always prohibited in WP10A

- resetting/reusing the consumed v0.4 token;
- resuming WP10-v0.4 scientific execution;
- creating a fresh June scientific token;
- changing the v0.4 preregistration or scientific grid;
- segmentation or stability scientific execution;
- interpreting capacity-only family outputs scientifically;
- method/family/representation/distance/sensitivity promotion;
- selector activation/replacement;
- canonical/R2 publication;
- Development/Validation consumption;
- provider intake/fetch;
- C2E/C2G/C2P/C2.5/C3 activation;
- probability, risk, exposure, trading or execution authority;
- force-push, destructive history rewrite or silent evidence deletion.

## 11. Gate sequence

### SRFDI-G10A — OPERATOR_REQUIRED

Allowed decisions:

- `SUPERSEDE`
- `DEFER`
- `BLOCK`
- `QUARANTINE`

`SUPERSEDE` means:

- preserve/admit exact PR #433 blocker evidence and consumed-token state;
- supersede only the failed WP10-v0.4 execution implementation route;
- authorize bounded WP10A capacity remediation;
- keep fresh scientific June execution denied.

### SRFDI-G10A-FREEZE — OPERATOR_REQUIRED

Prepared only after WP10A implementation/equivalence/capacity evidence.

Candidate decisions:

- `FREEZE_CAPACITY_REMEDIATION`
- `REDESIGN`
- `DEFER`
- `BLOCK`

A freeze still does not authorize a fresh scientific run.

### Fresh SRFDI-G-JUNE-AUTH

Required after a successful freeze. It must bind:

- unchanged v0.4 scientific preregistration hashes;
- unchanged source/population binding;
- new exact implementation commit/backend-pack hash;
- new authorized manifest;
- new one-run token.

No fresh run is implied by WP10A completion.

## 12. Rollback and failure behavior

If G10A is not approved, abandon only the preparation branch/PR. Preserve main,
PR #433 and all v0.4 evidence unchanged.

If WP10A later fails equivalence, stop and quarantine the candidate backend;
do not weaken the oracle or tests.

If WP10A is exact but still exceeds capacity, preserve the evidence and return
`REDESIGN_REQUIRED`; do not drop average linkage or any frozen configuration.

If external capacity artifacts are unavailable or fail hash verification, stop
`ARTIFACT_UNAVAILABLE`; do not reconstruct them outside the approved real-data
capacity-only scope.

## 13. Exact operator command

`OVC APPROVE SRFDI-G10A SUPERSEDE`

Until that decision is recorded, this contract grants **no implementation or
real-data capacity authority**.

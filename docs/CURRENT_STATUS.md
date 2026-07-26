# Current status

Snapshot date: 26 July 2026.
Merged main court-record tip reviewed: `dc05204becb2806fc10cab024d85ddab235326a7`.
RO2-G1 implementation and acceptance branch: `build/research-operations-v0-2-workspace-index` / PR `#71`.

## Integrated baseline

The reset, OPT-A v2 role-set activation, OPT-B.C1 v2 publication and shadow activation, Research Operations Foundation v0.1 activation, Research Console v0.3 Overview acceptance, OPT-B.C2 actual-parent reconciliation, C2-G4 exact-parent replay and C2-G5 local candidate freeze are merged into `main`.

Latest authority-changing or boundary-confirming records:

- OPT-A v2 A2-G5 selector activation: `docs/releases/opt-a-v2/activation/`
- OPT-B.C1 v2 B1-G5 shadow activation: `docs/releases/opt-b-c1-v2/b1-g5/`
- Research Operations v0.1 RO-G3 local activation: `docs/releases/research-operations-foundation/ro-g3/`
- Research Operations v0.2 RO2-G1 deterministic index acceptance: `docs/releases/research-operations-foundation-v0-2/ro2-g1/` on PR `#71`
- Research Console RC-G2-v0.3 Overview acceptance: `docs/releases/research-console-v0-3/rc-g2/`
- OPT-B.C2 C2-G3R actual-parent reconciliation: `docs/releases/opt-b-c2-v2/wp3-wp4-reconciliation/`
- OPT-B.C2 C2-G4 exact-parent replay: `docs/releases/opt-b-c2-v2/c2-g4/`
- OPT-B.C2 C2-G5 local candidate freeze: `docs/releases/opt-b-c2-v2/c2-g5/`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and prohibited as a selector, parent, parameter source or rollback target.

## Active OPT-A v2 role set

| Role | Release | Authority | Selector | Consumption |
|---|---|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `ACTIVE_DISCOVERY` | `ACTIVE` | `NOT_APPLICABLE` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `ACTIVE_DEVELOPMENT` | `ACTIVE` | `NOT_APPLICABLE` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `ACTIVE_VALIDATION` | `ACTIVE` | `LOCKED_UNCONSUMED` |

All three releases are remotely verified. The 21,410 quarantined derived-bucket records remain bound to `RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS` and cannot become downstream parents.

## OPT-B.C1 v2

B1-G5 result: `PASS — SHADOW ACTIVATION`.

| Role | Release | Selector | Records | Record files | Manifest SHA-256 |
|---|---|---|---:|---:|---|
| Discovery | `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1` | `SHADOW` | 159,892 | 144 | `6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2` |
| Development | `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1` | `SHADOW` | 52,872 | 48 | `ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017` |
| **Total** | **2 releases** | — | **212,764** | **192** | — |

The exact releases are frozen, QA-passed, remotely verified and selected for read, inspection and comparison as atomic derived facts. Validation C1 is not built. The exact C1 Discovery and Development releases were consumed only through the separately approved C2-G4 replay and C2-G5 local-candidate boundary.

## OPT-B.C2 v2

WP1-WP4 contracts, schemas, registries, fixtures, level/container/relation engines, parallel-state, persistence and transition logic are implemented. C2-G3R passed actual C1 plus exact OPT-A price-parent engine trust.

### C2-G4 exact-parent replay

Result: `PASS_LOCAL_REPLAY`.

- exact C1 and OPT-A parent chains: full-byte verified;
- input C1 records: 212,764;
- state records: 404,434;
- transition records: 323,910;
- rejected records: 0;
- output files: 24;
- output bytes: 872,839,722;
- source artifact: `8634383302`.

### C2-G5 local candidate freeze

Result: `PASS_LOCAL_CANDIDATE_RELEASE_FROZEN`.

Two independent materialisations of the C2-G4 outputs were byte-identical. Complete inventory and manifest binding, exact parent lineage, five independent axes, record uniqueness, transition endpoint closure and full-byte local verification passed. Blocking and unresolved QA issues are both zero.

| Role | Candidate release | Manifest | Manifest SHA-256 | State records | Transitions | Candidate artifact |
|---|---|---|---|---:|---:|---:|
| Discovery | `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1` | `MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1` | `c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33` | 303,856 | 245,752 | `8634699529` |
| Development | `OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1` | `MANIFEST.C2.OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1.r1` | `8a37e931ac003e88c8e1b3c4f8a1849e947f86f47e982e00ca4723e53fd9586e` | 100,578 | 78,158 | `8634700114` |

Candidate tree SHA-256: `f15ad152405708bca09e0255af6de69a4a54051e6f0f9e2128cd0c2944bf60fd`.

The candidates are `RELEASE_FROZEN / CANDIDATE / LOCAL_ONLY`. Publication, selector and activation remain `NONE`. Validation remains `LOCKED_UNCONSUMED`.

## Research Operations Foundation

### v0.1

RO-G3 result: `PASS`.

`OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.1` is accepted as `ACTIVE_RESEARCH_OPERATIONS_LOCAL` with append-only research records, local artifact and QA services, a replaceable typed read model and a local read-only console.

### v0.2

RO2-G1 result: `PASS_LOCAL_REPLACEABLE_DERIVED_INDEX`.

Accepted bounded local capabilities:

- deterministic Discovery and Development role-workspace indexes;
- deterministic observation and observation-family indexes;
- stable logical fixture index SHA-256 `dcb88c5f9c9fc0d4dbd12ac6a293607a1067fc11cfd9f19f72c4f497bd0da697`;
- Validation aggregate metadata projection only;
- Validation denial before path, object or row resolution;
- fail-closed unknown-role and conflicting-duplicate handling;
- no runtime writes.

Verification passed through 5 focused tests, two independent deterministic fixture builds and the 70-test full repository suite. The accepted index is replaceable and does not outrank its source releases or manifests. Quality, lineage, replay and release-difference implementation have not begun.

## Research Console v0.3

RC-G2-v0.3 result: `PASS`.

The unified shell, context-preserving navigation, Overview workspace and seven-domain ambient-health projection are accepted for bounded local read-only use. The Research workspace remains fixture-only pending `RC-WP3-v0.3 — Research workspace, replay, evidence and queue`. Mutating console authority and remote deployment remain denied.

## Active authority matrix

| Boundary | Current state | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / REMOTE_VERIFIED` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 role set | `A2_G5_PASS / ACTIVE` | `ACTIVE` |
| OPT-B.C1 v2 | `B1_G5_PASS / REMOTE_VERIFIED / SHADOW` | `SHADOW` |
| OPT-B.C2 v2 | `C2_G5_PASS / LOCAL_DISCOVERY_AND_DEVELOPMENT_CANDIDATES_FROZEN` | `NONE` |
| Research Operations v0.1 | `RO_G3_PASS / ACTIVE_RESEARCH_OPERATIONS_LOCAL` | Not applicable |
| Research Operations v0.2 | `RO2_G1_PASS / LOCAL_REPLACEABLE_DERIVED_INDEX` | Not applicable |
| Research Console v0.3 | `RC_G2_PASS / OVERVIEW_LOCAL_READ_ONLY / WP3_AUTHORISED` | Not applicable |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

## Retained authority boundaries

- Validation consumption remains `LOCKED_UNCONSUMED`.
- C2 candidates remain frozen local-only; publication, selector and activation authority remain absent.
- C2E, C2.5, C3 and new OPT-C/OPT-D authority remain absent.
- Probability, exposure, trading, execution and autonomous-agent authority remain `NONE`.
- Direct UI or RO2 writes to Git, R2, releases, selectors, thresholds or the primary branch remain denied.
- RO2-G1 grants only bounded local replaceable derived-index authority.

## Next boundaries

1. Merge PR `#71` after final CI confirms the RO2-G1 records and reconciled authority state.
2. Begin `RO2-WP2` only under a separate operator instruction.
3. Execute C2 publication-readiness and operator approval separately; do not write to R2, select or activate C2 before that gate passes.
4. Continue `RC-WP3-v0.3 — Research workspace, replay, evidence and queue` under the accepted read-only and fail-closed boundaries.

# Current status

Snapshot date: 26 July 2026.
Integrated `main` tip before this review: `dc05204becb2806fc10cab024d85ddab235326a7`.
C2 publication-readiness branch: `review/c2-publication-readiness` / PR `#72`.

## Integrated baseline

The repository reset, OPT-A v2 role-set activation, OPT-B.C1 v2 remote publication and shadow activation, Research Operations Foundation v0.1 activation, Research Console v0.3 Overview acceptance, OPT-B.C2 actual-parent reconciliation, C2-G4 exact-parent replay, C2-G5 local candidate freeze and Research Operations Foundation v0.2 design freeze are merged into `main`.

Latest authority-changing or boundary-confirming records:

- OPT-A v2 A2-G5 selector activation: `docs/releases/opt-a-v2/activation/`
- OPT-B.C1 v2 B1-G5 shadow activation: `docs/releases/opt-b-c1-v2/b1-g5/`
- Research Operations RO-G3 local activation: `docs/releases/research-operations-foundation/ro-g3/`
- Research Operations v0.2 RO2-G0 design freeze: `docs/releases/research-operations-foundation-v0-2/ro2-g0/`
- Research Console RC-G2-v0.3 Overview acceptance: `docs/releases/research-console-v0-3/rc-g2/`
- OPT-B.C2 C2-G3R actual-parent reconciliation: `docs/releases/opt-b-c2-v2/wp3-wp4-reconciliation/`
- OPT-B.C2 C2-G4 exact-parent replay: `docs/releases/opt-b-c2-v2/c2-g4/`
- OPT-B.C2 C2-G5 local candidate freeze: `docs/releases/opt-b-c2-v2/c2-g5/`
- OPT-B.C2 publication-readiness approval: `docs/releases/opt-b-c2-v2/publication-readiness/` on PR `#72`

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

The exact C1 releases remain frozen, QA-passed, remotely verified and selected as `SHADOW` atomic derived facts. Validation C1 is not built. The releases were consumed only through separately bounded C2-G4 replay, C2-G5 local freeze and the non-mutating publication-readiness review.

## OPT-B.C2 v2

WP1-WP4 contracts, schemas, registries, fixtures, level/container/relation engines, parallel-state, persistence and transition logic are implemented. C2-G3R passed actual C1 plus exact OPT-A price-parent engine trust.

### C2-G4 exact-parent replay

C2-G4 result: `PASS_LOCAL_REPLAY`.

- exact C1 and OPT-A parent chains: full-byte verified;
- input C1 records: 212,764;
- state records: 404,434;
- transition records: 323,910;
- rejected records: 0;
- output files: 24;
- output bytes: 872,839,722;
- source artifact: `8634383302`.

### C2-G5 local candidate freeze

C2-G5 result: `PASS_LOCAL_CANDIDATE_RELEASE_FROZEN`.

Two independent candidate materialisations were byte-identical. Complete inventory binding, exact parent lineage, five independent axes, record uniqueness, transition endpoint closure and full-byte local verification passed. Blocking and unresolved QA issues are zero.

| Role | Candidate release | Manifest | Manifest SHA-256 | State records | Transitions | Final candidate artifact |
|---|---|---|---|---:|---:|---:|
| Discovery | `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1` | `MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1` | `c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33` | 303,856 | 245,752 | `8634803012` |
| Development | `OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1` | `MANIFEST.C2.OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1.r1` | `8a37e931ac003e88c8e1b3c4f8a1849e947f86f47e982e00ca4723e53fd9586e` | 100,578 | 78,158 | `8634803579` |

Candidate tree SHA-256: `f15ad152405708bca09e0255af6de69a4a54051e6f0f9e2128cd0c2944bf60fd`.

The candidates remain `RELEASE_FROZEN / CANDIDATE / LOCAL_ONLY` until the approved R2 publication and full remote-verification operation completes.

### C2-PUB-G0 publication readiness and operator approval

Result: `PASS_PUBLICATION_READY_OPERATOR_APPROVED_EXACT_RELEASES_ONLY`.

Workflow run `30213663356` passed the canonical repository suite, verified the exact final GitHub artifact identities, downloaded both candidates, verified every manifest-bound byte and current contract/schema/registry/parameter-pack binding, confirmed exact OPT-A/C1 lineage, confirmed zero open QA issues and established that both exact R2 prefixes were absent without writing.

Review totals:

- releases: 2;
- manifest-bound files: 36;
- verified payload bytes: 872,867,602;
- state records: 404,434;
- transition records: 323,910;
- readiness receipt artifact: `8635181040`;
- receipt digest: `sha256:cc4f1a0997b56867a7a5cf8a03be3c326d275870d195039555c2c5eb0b45d27d`.

Authority after PASS:

- exact immutable R2 publication: `AUTHORISED_EXACT_RELEASES_ONLY`;
- publication execution: `NOT_YET_EXECUTED`;
- selector: `NONE`;
- activation: `NONE`;
- direct `ACTIVE_DISCOVERY`: denied until full remote verification and a separate selector/legacy-retirement transaction;
- Validation remains `LOCKED_UNCONSUMED`.

## Research Operations Foundation

RO-G3 result: `PASS`.

`OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.1` remains `ACTIVE_RESEARCH_OPERATIONS_LOCAL` with append-only records, audit, research CLI, artifact catalogue, no-mutation QA, deterministic read model and local read-only console authority.

Research Operations Foundation v0.2 has `RO2-G0 PASS_DESIGN_FREEZE`. It remains design canon only; RO2-WP1 runtime implementation has not begun. The RO2-G0 packet records the C2-G4 baseline at its freeze point and does not prevent later bounded C2 candidate or publication gates.

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
| OPT-B.C2 v2 | `C2_PUB_G0_PASS / PUBLICATION_AUTHORISED_NOT_EXECUTED / NO_C2_AUTHORITY` | `NONE` |
| Research Operations v0.1 | `RO_G3_PASS / ACTIVE_RESEARCH_OPERATIONS_LOCAL` | Not applicable |
| Research Operations v0.2 | `RO2_G0_PASS / DESIGN_CANON_ONLY` | Not applicable |
| Research Console v0.3 | `RC_G2_PASS / OVERVIEW_LOCAL_READ_ONLY / WP3_AUTHORISED` | Not applicable |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

## Retained authority boundaries

- Validation consumption remains `LOCKED_UNCONSUMED`.
- C2 selector and activation authority remain absent.
- No C2 remote bytes have been written by the readiness review.
- C2E, C2.5, C3 and new OPT-C/OPT-D authority remain absent.
- Probability, exposure, trading, execution and autonomous-agent authority remain `NONE`.
- Direct UI writes to Git, R2 or the primary branch remain denied.
- RO2-G0 grants design records and validators only; no RO2 runtime package has begun.

## Next boundaries

1. Review and merge PR `#72` so the publication-readiness workflow, exact approval and gate records become part of `main`.
2. Execute exact C2 Discovery and Development R2 publication using artifacts `8634803012` and `8634803579`, payload-first and manifest-last.
3. Perform full remote byte readback and commit the remote-verification receipt; stop with C2 selector and activation at `NONE`.
4. Only after remote verification, conduct a separate selector, B-STATE retirement and rollback-to-C1-only activation review.

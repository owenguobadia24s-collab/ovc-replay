# Current status

Snapshot date: 26 July 2026.
Latest integrated `main` tip reconciled into this branch: `28f0161580327a2222ae089a7ad01aa1dfc5f994`.
Main-to-RO2-WP1 reconciliation commit: `79b515540eb8de982ee8434479b709f98d2ffd2c`.
RO2-G1 branch: `build/research-operations-v0-2-workspace-index` / PR `#71`.

## Integrated baseline

The repository reset, OPT-A v2 role-set activation, OPT-B.C1 v2 remote publication and shadow activation, Research Operations Foundation v0.1 activation, Research Console v0.3 Overview acceptance, OPT-B.C2 actual-parent reconciliation, C2-G4 exact-parent replay, C2-G5 local candidate freeze, C2 publication-readiness approval, C2 R2 publication and full remote verification, and the C2 activation-readiness review are integrated into the reconciled baseline.

Latest authority-changing or boundary-confirming records:

- OPT-A v2 A2-G5 selector activation: `docs/releases/opt-a-v2/activation/`
- OPT-B.C1 v2 B1-G5 shadow activation: `docs/releases/opt-b-c1-v2/b1-g5/`
- Research Operations v0.1 RO-G3 local activation: `docs/releases/research-operations-foundation/ro-g3/`
- Research Operations v0.2 RO2-G0 design freeze: `docs/releases/research-operations-foundation-v0-2/ro2-g0/`
- Research Operations v0.2 RO2-G1 acceptance: `docs/releases/research-operations-foundation-v0-2/ro2-g1/`
- Research Console RC-G2-v0.3 Overview acceptance: `docs/releases/research-console-v0-3/rc-g2/`
- OPT-B.C2 C2-G4 exact-parent replay: `docs/releases/opt-b-c2-v2/c2-g4/`
- OPT-B.C2 C2-G5 local candidate freeze: `docs/releases/opt-b-c2-v2/c2-g5/`
- OPT-B.C2 publication readiness: `docs/releases/opt-b-c2-v2/publication-readiness/`
- OPT-B.C2 remote publication receipt: `docs/releases/opt-b-c2-v2/r2-publication/`
- OPT-B.C2 activation-readiness review: `docs/releases/opt-b-c2-v2/activation-review/`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and prohibited as a selector, parent, parameter source or rollback target.

## Active OPT-A v2 role set

| Role | Release | Authority | Selector | Consumption |
|---|---|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `ACTIVE_DISCOVERY` | `ACTIVE` | `NOT_APPLICABLE` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `ACTIVE_DEVELOPMENT` | `ACTIVE` | `NOT_APPLICABLE` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `ACTIVE_VALIDATION` | `ACTIVE` | `LOCKED_UNCONSUMED` |

All three releases are remotely verified. The 21,410 quarantined derived-bucket records remain excluded from accepted-observation parentage.

## OPT-B.C1 v2

B1-G5 result: `PASS — SHADOW ACTIVATION`.

| Role | Release | Selector | Records | Record files | Manifest SHA-256 |
|---|---|---|---:|---:|---|
| Discovery | `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1` | `SHADOW` | 159,892 | 144 | `6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2` |
| Development | `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1` | `SHADOW` | 52,872 | 48 | `ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017` |
| **Total** | **2 releases** | — | **212,764** | **192** | — |

Validation C1 is not built. C1 remains the exact shadow fact parent used by bounded C2 work.

## OPT-B.C2 v2

### C2-G4 exact-parent replay

Result: `PASS_LOCAL_REPLAY`.

- input C1 records: 212,764;
- state records: 404,434;
- transition records: 323,910;
- rejected records: 0;
- output files: 24;
- output bytes: 872,839,722.

### C2-G5 local candidate freeze

Result: `PASS_LOCAL_CANDIDATE_RELEASE_FROZEN`.

| Role | Release | Manifest SHA-256 | State records | Transitions |
|---|---|---|---:|---:|
| Discovery | `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1` | `c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33` | 303,856 | 245,752 |
| Development | `OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1` | `8a37e931ac003e88c8e1b3c4f8a1849e947f86f47e982e00ca4723e53fd9586e` | 100,578 | 78,158 |

Candidate tree SHA-256: `f15ad152405708bca09e0255af6de69a4a54051e6f0f9e2128cd0c2944bf60fd`.

### C2 R2 publication and remote verification

Result: `PASS_FULL_REMOTE_BYTE_VERIFICATION`.

- workflow run: `30214691361`;
- source candidate run: `30212281089`;
- remote objects verified: 38;
- remote bytes verified, including manifests: 872,884,406;
- receipt artifact: `8635489071`;
- receipt digest: `sha256:36cccd49982b5c9d79f2206e5328cb884bf93c0f6ff17df08c3d216f4069b0c1`.

Both exact C2 releases are now remotely available and fully verified. Publication grants remote availability only.

### C2 activation-readiness review

Result: `PASS_READY_FOR_EXPLICIT_ACTIVATION_DECISION_NOT_ACTIVATED`.

- C2 selector: `NONE`;
- C2 activation: `NONE`;
- B-STATE retirement executed: `NO`;
- rollback target if later activated: C2 selectors `NONE` / C1-only operation;
- Validation: `LOCKED_UNCONSUMED`.

The next C2 gate is `C2_ACTIVE_DISCOVERY_SELECTOR_AND_LEGACY_RETIREMENT_OPERATOR_DECISION`.

## Research Operations Foundation

### v0.1

RO-G3 remains `PASS / ACTIVE_RESEARCH_OPERATIONS_LOCAL`.

### v0.2

RO2-G1 result: `PASS_LOCAL_REPLACEABLE_DERIVED_INDEX`.

Accepted bounded local capabilities:

- deterministic Discovery and Development role-workspace indexes;
- deterministic observation and observation-family indexes;
- logical fixture index SHA-256 `dcb88c5f9c9fc0d4dbd12ac6a293607a1067fc11cfd9f19f72c4f497bd0da697`;
- Validation aggregate metadata only;
- Validation denial before path, object or row resolution;
- fail-closed unknown-role and conflicting-duplicate handling;
- no runtime writes.

Verification basis: 5 focused RO2-WP1 tests, two independent deterministic fixture builds and the 70-test full repository suite. The index is replaceable and does not outrank source releases or manifests.

RO2-G1 neither performed nor authorised the C2 publication, selector or activation transactions. It only recognises the separately completed remote-verification court record.

## Research Console v0.3

RC-G2-v0.3 remains `PASS`. The Overview is accepted for bounded local read-only use; the Research workspace remains fixture-only pending RC-WP3-v0.3.

## Active authority matrix

| Boundary | Current state | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / REMOTE_VERIFIED` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 role set | `A2_G5_PASS / ACTIVE` | `ACTIVE` |
| OPT-B.C1 v2 | `B1_G5_PASS / REMOTE_VERIFIED / SHADOW` | `SHADOW` |
| OPT-B.C2 v2 | `REMOTE_VERIFIED / ACTIVATION_READY_NOT_ACTIVATED` | `NONE` |
| Research Operations v0.1 | `RO_G3_PASS / ACTIVE_RESEARCH_OPERATIONS_LOCAL` | Not applicable |
| Research Operations v0.2 | `RO2_G1_PASS / LOCAL_REPLACEABLE_DERIVED_INDEX` | Not applicable |
| Research Console v0.3 | `RC_G2_PASS / OVERVIEW_LOCAL_READ_ONLY` | Not applicable |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

## Retained authority boundaries

- Validation remains `LOCKED_UNCONSUMED`.
- C2 selector and activation remain `NONE`.
- B-STATE retirement has not executed.
- C2E, C2.5, C3 and new OPT-C/OPT-D authority remain absent.
- Probability, exposure, trading, execution and autonomous-agent authority remain `NONE`.
- Direct UI or RO2 writes to Git, R2, releases, selectors, thresholds or the primary branch remain denied.
- RO2-G1 grants only bounded local replaceable derived-index authority.

## Next boundaries

1. Merge PR `#71` after final reconciled CI passes.
2. Begin `RO2-WP2` only under a separate operator instruction.
3. Handle the C2 selector/B-STATE retirement transaction only through its separate explicit operator gate.

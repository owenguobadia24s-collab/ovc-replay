# C2-G5 — local Discovery and Development candidate freeze

## Decision

**PASS_LOCAL_CANDIDATE_RELEASE_FROZEN — the accepted C2-G4 exact-parent replay was converted into deterministic, role-aware, locally frozen C2 Discovery and Development candidate release roots.**

The candidates passed complete inventory binding, two-run byte-equivalence, full-byte local verification, record-identity checks, exact parent-lineage checks, five-axis checks and transition-endpoint closure. No blocking or unresolved QA issue remains.

## Execution

- Workflow: `C2-G5 local candidate freeze and QA`
- Workflow run: `30211911410`
- Branch: `exec/c2-g5-candidate-freeze`
- Execution source commit: `2bf24c56fde3ff773e8e265d17982754cbe38ef7`
- Source replay artifact: `8634383302`
- Source replay artifact digest: `sha256:b8f993f733aed75e488aa60883f00a53596c15e5cd6c14edb787fc3bc12df62f`

## Verification result

| Verification | Result |
|---|---|
| Source replay outputs | 24 files / 872,839,722 bytes |
| State records | 404,434 |
| Transition records | 323,910 |
| Rejected records | 0 |
| Duplicate record IDs | 0 |
| Independent materialisation equivalence | `PASS_TWO_INDEPENDENT_BYTE_IDENTICAL_MATERIALIZATIONS` |
| Candidate tree SHA-256 | `f15ad152405708bca09e0255af6de69a4a54051e6f0f9e2128cd0c2944bf60fd` |
| Full-byte local verification | `PASS` |
| Blocking QA issues | 0 |
| Unresolved QA issues | 0 |

## Frozen candidates

| Role | Release | Manifest | Manifest SHA-256 | State records | Transitions | Manifest-bound bytes |
|---|---|---|---|---:|---:|---:|
| Discovery | `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1` | `MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1` | `c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33` | 303,856 | 245,752 | 659,484,886 |
| Development | `OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1` | `MANIFEST.C2.OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1.r1` | `8a37e931ac003e88c8e1b3c4f8a1849e947f86f47e982e00ca4723e53fd9586e` | 100,578 | 78,158 | 213,382,716 |

Each candidate contains six state files, six transition files, a release descriptor, exact C2-G4 source receipts and binding, a QA summary, an issue ledger and a self-bound manifest.

## Workflow artifacts

- Discovery candidate: `8634699529`
  - digest: `sha256:3f07105e27420157656e64445515bdeb6ad62ea3beddc9761b32656ea5d81d47`
- Development candidate: `8634700114`
  - digest: `sha256:f9b80f652a38c1e5b6137e97226488809481407ea93139fe03d7aea268448083`
- Gate packet: `8634700203`
  - digest: `sha256:2b4c2c902ca52c7d4359ea7df3c9d0c52df866957f76fe7d1e70779306fa4e59`
- Retention expiry: `2026-10-24T17:07:21Z`

## Authority retained

- Candidate lifecycle: `RELEASE_FROZEN / CANDIDATE / LOCAL_ONLY`
- Validation consumption: `LOCKED_UNCONSUMED`
- Publication: `NONE`
- Selector: `NONE`
- Activation: `NONE`
- C2E, C2.5, C3, OPT-C and OPT-D authority: unchanged
- Probability, exposure, trading and execution: `NONE`

## Next boundary

A separate C2 publication-readiness and operator-approval gate is required. It must review these exact candidate manifests and artifact identities before any R2 write. Publication, selector mutation and direct `ACTIVE_DISCOVERY` activation remain separate decisions.

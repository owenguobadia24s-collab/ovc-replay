# C1C-G3 — C1 v2 R2 publication and full remote verification

**Decision:** `PASS`

- Workflow run: `30384400312`
- Workflow commit: `1e2a1960ff0eb6747998453e5693cc82856524ba`
- Source candidate run: `30370847916`
- Remote objects verified: `194`
- Remote bytes verified including manifests: `36206001`
- Publication order: payload first, manifest completion marker last
- C1 selectors: unchanged pending coordinated C1C-G4/G5 transaction
- C2: unchanged pending C1C-G5
- Validation: `LOCKED_UNCONSUMED`

## Releases

| Role | Release | Manifest | Logical SHA-256 | File SHA-256 | Collision state | Objects |
|---|---|---|---|---|---|---:|
| DISCOVERY | `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2` | `MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2.r1` | `c9b2eaa826419a510504c016d99072c6015c337a5c2ef435252d5f6ff1db93bf` | `708025a0f96db4649996bc1201da258f76c048723cf29b0c82725a19ba6418a9` | EXACT_EXISTING_REVERIFY | 145 |
| DEVELOPMENT | `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2` | `MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2.r1` | `e4f1a2d0af7064837003f1c7b56156966aba3b035cc9a7b8ebbdc8b6b181d73f` | `56c42c1d34d77670ffec25dcf86da6bd7726017c133f1bd9e4f4be2aba23633e` | EXACT_EXISTING_REVERIFY | 49 |

Rollback leaves the exact v2 releases immutable and inactive and retains the existing v1 selectors.

Next: execute deterministic C2 v2 identity replay and remote verification under C1C-G5.

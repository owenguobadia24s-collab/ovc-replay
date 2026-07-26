# OPT-B.C2 v2 — R2 publication and full remote verification

**Decision:** PASS — the exact approved Discovery and Development C2 candidates were published immutably to R2 using payload-first, manifest-last ordering, and every remote byte was read back and SHA-256 verified.

- Workflow run: `30214691361`
- Source candidate run: `30212281089`
- Remote objects verified: `38`
- Remote bytes verified, including manifests: `872884406`
- Receipt artifact: `8635489071`
- Receipt digest: `sha256:36cccd49982b5c9d79f2206e5328cb884bf93c0f6ff17df08c3d216f4069b0c1`

| Role | Release | Manifest | Remote objects | Payload bytes |
|---|---|---|---:|---:|
| Discovery | `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1` | `MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1` | 19 | 659484886 |
| Development | `OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1` | `MANIFEST.C2.OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1.r1` | 19 | 213382716 |

Publication grants remote availability only. C2 selector and activation remain `NONE`; Validation remains `LOCKED_UNCONSUMED`.

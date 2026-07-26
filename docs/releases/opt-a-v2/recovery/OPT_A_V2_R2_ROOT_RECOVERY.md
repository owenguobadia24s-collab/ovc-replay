# OPT-A v2 — exact Discovery and Development root recovery

## Decision

**PASS — the exact active OPT-A v2 Discovery and Development release roots were recovered from canonical Cloudflare R2 and full-byte verified against the frozen C2 price-parent contract.**

The operation was read-only against R2. It did not retrieve Validation, mutate a remote object, change a selector, run C2 market replay or create a candidate release.

## Execution

- Workflow: `OPT-A v2 exact R2 parent-root recovery`
- Run: `30209041054`
- Workflow source commit: `27b1bb503031afb4c3d4615c2f40d035e2b39e79`
- Result: `SUCCESS`
- Receipt: `OPT_A_V2_R2_ROOT_RECOVERY_RECEIPT.json`

## Recovered roots

| Role | Release | Manifest | Payload objects | Payload bytes | Price files | Verification |
|---|---|---|---:|---:|---:|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2` | 293 | 155,632,392 | 144 | `PASS_C2_EXACT_PRICE_PARENT_CONTRACT` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r2` | 101 | 52,762,768 | 48 | `PASS_C2_EXACT_PRICE_PARENT_CONTRACT` |
| **Total** | **2 roots** | — | **394** | **208,395,160** | **192** | **PASS** |

The verifier checked the exact manifest SHA-256, every declared local path, every payload byte count and SHA-256, release identity, manifest identity, descriptor binding, price-file inventory and clock/side scope inventory.

## Recovery artifacts

### Exact parent roots

- Artifact ID: `8633917454`
- Name: `opt-a-v2-r2-exact-parent-roots`
- Artifact digest: `sha256:6ba85619d21e4ac84bab2838adb237c4cb8fdd5b69bacd185c862712ddd8e47e`
- Retained until: `2026-10-24T15:49:48Z`

The extracted artifact is already shaped for the C2 runner:

```text
<opt-a-release-root>/
├── discovery/
│   ├── manifest.json
│   └── files/
└── development/
    ├── manifest.json
    └── files/
```

### Verification report

- Artifact ID: `8633917538`
- Name: `opt-a-v2-r2-root-recovery-report`
- Artifact digest: `sha256:3bdf7a75f452606d0bb2b3ba93b728693bee28ea6b87fac10e12b8fcfa70b037`
- Retained until: `2026-10-24T15:49:48Z`

## Authority retained

- OPT-A active selectors and remote releases are unchanged.
- Validation remains `LOCKED_UNCONSUMED` and was not downloaded.
- C2 market replay remains `NOT_EXECUTED`.
- C2 candidate release, publication, selector and activation remain `NONE`.
- Probability, exposure, trading and execution remain `NONE`.

## Next bounded operation

Use artifact `8633917454` as the exact `--opt-a-release-root` input for the separately authorised C2 WP5 replay. The root supplied to the runner must contain the `discovery/` and `development/` children exactly as recovered.

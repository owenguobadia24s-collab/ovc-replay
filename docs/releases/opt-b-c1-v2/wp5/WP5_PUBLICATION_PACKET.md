# OPT-B.C1 v2 WP5 — R2 publication and full remote verification

**Decision: PASS.** The exact WP4F Discovery and Development C1 releases are present under their immutable R2 release/manifest keys, and the reconciliation verification step read and SHA-256 checked every remote object successfully.

## Evidence

- Source WP4F workflow run: `30187276514`
- Remote reconciliation workflow run: `30190733324`
- Remote reconciliation step: `Reconcile exact bytes and verify remote — success`
- Published releases: `2`
- Remote objects verified: `194`
- Remote bytes verified, including both manifests: `36,203,151`
- Publication identity: exact WP4F frozen manifests only
- Existing objects: accepted only after exact size and SHA-256 equality
- Missing objects: eligible only for immutable upload
- Manifest role: completion marker

## Published releases

| Role | Release | Manifest | Manifest SHA-256 | Objects |
|---|---|---|---|---:|
| Discovery | `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1` | `MANIFEST.C1.OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1.r1` | `6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2` | 145 |
| Development | `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1` | `MANIFEST.C1.OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1.r1` | `ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017` | 49 |

## Retained authority boundary

- C1 selector: `NONE`
- C2 consumption: `DENIED_PENDING_SEPARATE_HANDOFF_REVIEW`
- Validation: `LOCKED_UNCONSUMED`
- Probability, exposure, trading and execution authority: `NONE`
- Next authority-changing review: post-publication review before any selector or handoff decision

The workflow's final repository-push step failed because it targeted a pre-existing divergent branch. That transport failure occurred after remote reconciliation, full-byte verification and registry generation had all succeeded. This packet reconciles the successful evidence into the repository without changing the verified remote objects.

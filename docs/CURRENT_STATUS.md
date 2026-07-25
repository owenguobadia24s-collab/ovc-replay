# Current status

Snapshot date: 25 July 2026.

## Repository baseline

R0 PR #2 and WP1 PR #3 are merged. WP2 starts from `main` commit `5c567c1ba7de57d83079200c006f991d41642310`.

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and non-reproducible from the exact sealed bytes. The three v2 role identities remain registered with every selector at `NONE`; 2025 validation remains `LOCKED_UNCONSUMED`.

## OPT-A v2 WP2 — evidence-store lifecycle extension

WP2 extends the retained `ovc_evidence_store` core with:

- process-only `OVC_EXTERNAL_ARTIFACT_ROOT` resolution and repository separation;
- safe `init-workspace` creation with no provider or R2 side effects;
- deterministic exact-byte workspace inventories;
- `freeze-release` with QA PASS, inventory matching and no-overwrite controls;
- predecessor/supersession validation and release-ID reuse denial;
- manifest-bound publication approval validation;
- non-destructive publication readiness with explicit `READY`, `BLOCKED` and `NOT_EVALUABLE` results;
- an upload CLI gate requiring an exact publication approval before rclone can run;
- Windows operator guidance and lifecycle/readiness tests.

The original deterministic manifest, immutable payload-first/manifest-last upload and full remote byte-verification code remains in place.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / WP2_LIFECYCLE_IMPLEMENTED` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 programme | `WP1_GOVERNANCE_ONLY` | `NONE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

## External evaluation boundary

Credential-free CI tests lifecycle and remote-readiness behaviour with synthetic files and mocked read-only rclone responses. It does not inspect the operator's Windows artifact root, expose environment-only R2 credentials, read the current bucket lock or mutate R2.

## Not authorised

Provider download, GBP/USD population creation, role-release construction, canonical R2 publication, selector activation, validation consumption, OPT-B/C/D semantic claims, probability, exposure, trading and execution remain unauthorised.

## Next gate

Review and merge WP2. WP3 may proceed independently after WP1. Actual population execution remains blocked until A2-G0 passes.

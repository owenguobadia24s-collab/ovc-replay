# Current status

Snapshot date: 25 July 2026.

## Repository reset baseline

R0 PR #2 is merged into `main` at `a9902c97e21131b1882b4c11ca3a2a79273e7c77`. The merge contains reviewed reset head `71c7c5513efb9bb8d214d118be03090664050c21`. Historical executable machinery, release records and superseded decisions remain quarantined; the evidence-store infrastructure and clean OPT-A/C1/C2 namespaces remain active.

## OPT-A v2 WP1 — release governance

WP1 records the exact OPT-A v2 programme identity and the disposition of historical `OPT-A.GBPUSD.2026H1.v1`.

- v1 disposition: `SUPERSEDED_UNPUBLISHED`
- exact v1 payload: unavailable; 14 expected artifacts totalling 13,906,357 bytes
- v1 reproducibility: `NOT_REPRODUCIBLE_MISSING_PAYLOAD`
- v1 R2 canonical state: `ABSENT`
- new bytes under the v1 identity: prohibited
- v2 release set: `OPT-A.GBPUSD.ROLESET.2021_2025.v1`
- discovery identity: `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2`
- development identity: `OPT-A.GBPUSD.DEVELOPMENT.2024.v2`
- validation identity: `OPT-A.GBPUSD.VALIDATION.2025.v2`
- validation consumption: `LOCKED_UNCONSUMED`
- role selectors: all `NONE`

WP1 creates governance contracts, schemas, registries, recovery/supersession records and tests only. It does not download provider data, build a market release, publish to R2 or activate selectors.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 programme | `WP1_GOVERNANCE_ONLY` | `NONE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

## Not yet authorised

Provider download, role-release construction, v2 canonical publication, selector activation, validation consumption, OPT-B/C/D semantic claims, probability, exposure, trading and execution remain unauthorised.

## Next gate

Review and merge WP1. After WP1 PASS is merged, WP2 evidence-store lifecycle extension and WP3 provider/clock/release-split contracts may begin on separate branches. Population execution remains blocked until A2-G0 passes.

# OPT-A v2 Programme Ratification v0.2

## Decision

The operator instruction to execute WP1 ratifies `OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2` for bounded, gate-controlled execution. WP1 records programme identity and v1 disposition only. Later work packets remain subject to their predecessor gates and exact operator approvals.

## Source document identity

- Document title: `OVC OPT-A v2 GBP/USD Population Intake and Role-Split Release Programme Implementation Plan v0.2`
- Document ID: `OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2`
- Uploaded file SHA-256: `e0e9b0f545b3d5b147000ff69bf501b57874f2e8ee4aba84c4f6c4475cb9e0f6`
- Supersedes: `OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.1`
- Ratification date: 25 July 2026

## Repository baseline

- Repository: `owenguobadia24s-collab/ovc-replay`
- R0 PR: `#2`, merged
- WP1 baseline commit: `a9902c97e21131b1882b4c11ca3a2a79273e7c77`
- Required R0 reset head included by merge: `71c7c5513efb9bb8d214d118be03090664050c21`
- WP1 branch: `build/opt-a-v2-release-governance`

## Fixed programme identity

- Instrument: GBP/USD (`GBPUSD`)
- Provider: Dukascopy
- Population interval: `[2021-01-01T00:00:00Z, 2026-01-01T00:00:00Z)`
- Native source objects: monthly M1 BID, M1 ASK, H1 BID and H1 ASK
- Discovery release: `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2`
- Development release: `OPT-A.GBPUSD.DEVELOPMENT.2024.v2`
- Validation release: `OPT-A.GBPUSD.VALIDATION.2025.v2`
- Release set: `OPT-A.GBPUSD.ROLESET.2021_2025.v1`
- Selector set: `SELECTOR.OPT-A.GBPUSD.ROLESET.v1`
- Validation default: `LOCKED_UNCONSUMED`

## Authority granted by this record

WP1 may create governance contracts, schemas, registries, recovery and supersession records, tests and status documentation.

After WP1 passes and merges, WP2 and WP3 are authorised to begin on separate branches. Provider population download remains blocked until A2-G0 passes. R2 upload, selector activation, validation consumption, OPT-B/C/D claims, probability, exposure, trading and execution remain unauthorised.

# WP3 Provider, Clock, Release-Split and Handoff Contract Summary

## Result scope

WP3 freezes the contract surface required before OPT-A v2 provider execution. It introduces no provider bytes or market authority.

## Fixed provider population

- Provider: Dukascopy
- Instrument: GBP/USD (`GBPUSD`)
- Native source families: monthly M1 BID, M1 ASK, H1 BID and H1 ASK
- Population interval: `[2021-01-01T00:00:00Z, 2026-01-01T00:00:00Z)`
- Source objects: immutable byte-bound identities with intake records and schema fingerprints

## Fixed role split

| Role | Release ID | Interval | Selector |
|---|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `[2021-01-01, 2024-01-01)` UTC | `NONE` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `[2024-01-01, 2025-01-01)` UTC | `NONE` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `[2025-01-01, 2026-01-01)` UTC | `NONE` |

Validation remains `LOCKED_UNCONSUMED`.

## Fixed clock and lineage

- UTC half-open intervals only
- 15M = exact 15 M1 parents
- `H1_M1_DERIVED` = exact 60 M1 parents
- `H1_PROVIDER_NATIVE` = independent corroboration identity
- A-L 2H spine = exact 120-M1 chain on fixed UTC boundaries
- Optional 4H = 240 M1 parents
- Optional D1 = 1,440 M1 parents
- no interpolation, fills, synthetic flat candles or H1 substitution for missing M1

## Fixed reconciliation and handoff

H1 reconciliation compares provider-native and M1-derived bars by exact UTC interval and canonical decimal values. It may report matches, mismatches or missing objects, but it may never substitute one chain for the other.

OPT-B.C1 may later consume only a sealed handoff bound to one exact release ID, manifest ID, inventory hash, source commit, remote verification receipt, contract set and selector decision. Mutable workspace scanning and historical v1 fallback are prohibited.

## Synthetic fixtures

The WP3 fixture pack contains:

- 4 provider-intake records
- 4 source-object identities
- 3 clock/bucket cases
- 2 reconciliation records
- 1 draft handoff record

Every fixture is synthetic, non-authoritative and denied as provider evidence, release parent, discovery seed, selector input or OPT-B handoff.

## Deferred authority

Actual provider download, release construction, R2 publication, selector activation, validation consumption and OPT-B replay remain blocked. The next programme decision is `A2-G0 — foundation review` after WP2 and WP3 are merged.
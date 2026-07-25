# Current status

Snapshot date: 25 July 2026.

## Repository reset

R0-1, R0-2 and R0-3 have passed. The historical v1 repository is frozen at `c0ad7ba22618babdde731e2a338f68f688d4210c`, 339 tracked files were classified, and 106 legacy executable files were moved with exact byte identity into `legacy/quarantine/abcd-engine-v1-c0ad7ba/`.

R0-4 established the clean active-tree foundation. R0-5 installed 42 compact synthetic OPT-A, C1 and C2 fixture cases. R0-6 installed six repository authority guard families with 14 test methods in the standard CI suite. The fixtures and guards remain non-authoritative and do not activate any research release.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE` | Not applicable |
| OPT-A v1 | `HISTORICAL_SUPERSEDED` | `NONE` |
| OPT-A v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E | `DEFERRED` | `NONE` |
| C2.5 | `DEFERRED` | `NONE` |
| C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

## Active repository responsibilities

- Preserve immutable history, decisions and release records.
- Maintain deterministic evidence-store infrastructure.
- Provide clean OPT-A, C1 and C2 package and governance namespaces.
- Maintain compact synthetic fixtures for contract and implementation testing.
- Enforce quarantine import, namespace, selector, discovery seed, dependency and storage-plane guards through CI.

## Not yet authorised

Provider download, OPT-A v2 release creation, C1 or C2 market replay, R2 canonical publication for the new line, selector activation, C2E, C2.5, C3, OPT-C, OPT-D, probability, exposure and execution.

## Next gate

`R0-7 — final validation and operator packet`.

# C2AR Authority, Capacity and Artifact Contract v0.1

Programme: `OVC-C2-ANATOMY-REDESIGN-v0.2`  
Plan: `OVC-C2-ANATOMY-REDESIGN-IMPLEMENTATION` / `0.2-REVISED`  
Baseline: `a15301935c037b64cd459da49dd6a75a58014b25`

## Authority

WP0 may create repository controls, schemas, registries, inventories, QA and non-destructive branches. It may not alter active C2 selectors, formulas, thresholds, clocks, lattices, releases, R2 publication, Validation, C2E, C2.5, C3, probability, risk, exposure, trading, execution or agent-write authority.

## Frozen operational budgets

| Plane | Budget | Failure behavior |
|---|---:|---|
| Focused CI elapsed time | 900 seconds | `CAPACITY_EXCEEDED` |
| Focused CI peak RSS | 2048 MiB | `CAPACITY_EXCEEDED` |
| Single Git artifact | 5,000,000 bytes | externalise and hash |
| Packet Git delta | 25,000,000 bytes | split bounded packet or externalise |
| Operator-local full replay | 14,400 seconds | preserve restart manifest and stop |
| Retained external packet output | 10,000,000,000 bytes | preserve compact diagnostic manifest and stop |

Silent sampling, evidence dropping and denominator changes are prohibited. A capacity failure preserves partial diagnostics, exact restart point, source identities and unchanged authority.

## Artifact boundary

Git contains contracts, schemas, registries, compact fixtures, deterministic code, tests, manifests, hashes, QA, decisions and programme state. Raw market data, caches, replay tables, graph stores, parameter surfaces, rendered review bundles and bulky benchmarks remain under `OVC_EXTERNAL_ARTIFACT_ROOT` or another separately approved immutable store. R2 write authority is none.

## Rollback

Revert the bounded packet. Do not delete accepted evidence or rewrite history. Active C2 remains unchanged.

# R0-3 Exact-Path Quarantine Migration Decision

- Baseline: `c0ad7ba22618babdde731e2a338f68f688d4210c`
- Migration commit: `1cdd8d95c14eeca5cdd32746277083d433a445e1`
- Approved moves: **106**
- Executed moves: **106**
- Source paths remaining: **0**
- Missing quarantine targets: **0**
- Duplicate source or target paths: **0**
- Git blob identity: **PASS**
- SHA-256 byte identity: **PASS**
- Historical `docs/history/` release records moved: **0**
- Active-tree post-move tests: **24 passed**
- Decision: `PASS_R0_3`

The approved legacy ABCD contracts, implementation packages, scripts and associated tests now reside under `legacy/quarantine/abcd-engine-v1-c0ad7ba/` with unchanged bytes and an exact original-path crosswalk. The quarantine has no active package, test, selector, release-parent, rollback-target, parameter-source or discovery-seed authority.

The evidence-store package and its active regression suite remain outside quarantine. No provider intake, external artifact transfer, R2 publication, selector activation, market claim, probability, exposure or execution authority occurred.

R0 may progress to **R0-4 Active-Tree Foundation**. The reset pull request remains draft and unmerged.
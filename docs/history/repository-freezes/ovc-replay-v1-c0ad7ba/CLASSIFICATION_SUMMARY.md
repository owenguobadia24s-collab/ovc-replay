# R0-2 Tracked-File Classification Summary

- Baseline: `c0ad7ba22618babdde731e2a338f68f688d4210c`
- Files classified: **339**
- Unresolved files: **0**
- Files moved in R0-2: **0**
- Quarantine destination reserved: `legacy/quarantine/abcd-engine-v1-c0ad7ba/`
- Decision state: `CLASSIFIED_NO_MOVES_EXECUTED`

| Classification | Files | Frozen blob bytes | R0-2 consequence |
|---|---:|---:|---|
| `MOVE_TO_QUARANTINE` | 106 | 906729 | Approved for an exact-path move during R0-3; not moved yet. |
| `REBUILD_V2` | 3 | 6350 | Stay in place until replaced atomically by the v2 scaffold. |
| `REMOVE_GENERATED` | 0 | 0 | Approved for removal only during a later bounded packet. |
| `RETAIN_ACTIVE` | 13 | 45691 | Remain in the active tree as infrastructure or repository control. |
| `RETAIN_HISTORICAL` | 217 | 2772011 | Remain immutable and addressable without active model authority. |
| `UNRESOLVED` | 0 | 0 | Blocks progression. |

## Classification principles

- `docs/history/` and prior architecture records remain historical court records and are not moved.
- `src/ovc_evidence_store/`, its test and evidence-store boundary documentation remain active infrastructure.
- Existing ABCD contracts, source packages, scripts and associated tests are assigned to quarantine.
- `README.md`, `pyproject.toml` and `docs/CURRENT_STATUS.md` are marked for atomic v2 rewrite rather than deletion.
- No old story, threshold, state, outcome or candidate receives active authority through retention.

## R0-2 result

**PASS — every frozen baseline file has exactly one classification and no repository path was moved.**

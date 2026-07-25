# R0-2 Tracked-File Classification Decision Record

- Repository: `owenguobadia24s-collab/ovc-replay`
- Baseline: `c0ad7ba22618babdde731e2a338f68f688d4210c`
- Reset branch: `build/v2-foundation-reset`
- Classification schema: `ovc-r0-tracked-file-classification/v1`
- Classification SHA-256: `d87725692d5099c31ec53214f4c8fcf2446b673607a4714ee347ed693007dd63`
- Decision: **PASS**
- Authority delta: **classification only; no path move, deletion, selector change or runtime activation**

## Results

- Frozen files classified: **339**
- `MOVE_TO_QUARANTINE`: **106**
- `REBUILD_V2`: **3**
- `RETAIN_ACTIVE`: **13**
- `RETAIN_HISTORICAL`: **217**
- `REMOVE_GENERATED`: **0**
- `UNRESOLVED`: **0**

Every file in the frozen baseline has exactly one disposition. Every proposed quarantine move preserves the original relative path beneath `legacy/quarantine/abcd-engine-v1-c0ad7ba/`. No duplicate source path or duplicate quarantine target exists.

## Boundary decisions

1. `docs/history/` remains in place as the immutable historical court record.
2. Prior architecture and development summaries remain historical source material without active model authority.
3. `src/ovc_evidence_store/`, `tests/test_evidence_store.py`, and the evidence-store boundary documentation remain active infrastructure.
4. Existing ABCD contracts, source packages, scripts and associated tests are approved for quarantine in R0-3.
5. `README.md`, `pyproject.toml` and `docs/CURRENT_STATUS.md` remain in place until an atomic v2 rewrite.
6. Retention never grants legacy stories, thresholds, selectors, states, outcomes or candidates authority in the v2 discovery line.

## Progression

R0-2 is closed as `PASS`. R0-3 may execute only the exact moves recorded in `QUARANTINE_MOVE_PLAN.json`; it may not broaden the move set, delete historical records, alter the evidence-store package or activate any v2 model authority without a separately recorded decision.

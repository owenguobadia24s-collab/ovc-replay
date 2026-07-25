# R0-1 Baseline Preflight Report

| Check | Result | Evidence |
|---|---:|---|
| Baseline commit is present | true | `git cat-file -e c0ad7ba22618babdde731e2a338f68f688d4210c^{commit}` |
| Remote main equals approved baseline | true | `c0ad7ba22618babdde731e2a338f68f688d4210c` |
| Archive branch equals approved baseline | true | `c0ad7ba22618babdde731e2a338f68f688d4210c` |
| Python environment setup | 0 | `PYTHON_ENVIRONMENT.log` |
| Editable baseline install | 0 | `PYTHON_ENVIRONMENT.log` |
| Source compile check | 0 | `COMPILEALL.log` |
| Baseline pytest suite | 0 | `PYTEST_BASELINE.log` |
| Inventory generated | PASS | 339 tracked files |
| Exact SHA-256 ledger generated | PASS | `TRACKED_FILE_HASHES.json` |
| Selector/status snapshot generated | PASS | `ACTIVE_SELECTOR_SNAPSHOT.json` |

## Pytest tail

```
............................................................... [ 48%]
....................................................................     [100%]
131 passed, 9 subtests passed in 0.97s
```

**R0-1 status: PASS**

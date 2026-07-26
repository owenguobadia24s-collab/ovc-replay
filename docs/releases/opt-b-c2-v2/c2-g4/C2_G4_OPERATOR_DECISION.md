# C2-G4 — exact-parent Discovery and Development market replay

## Decision

**PASS_LOCAL_REPLAY — the exact manifest-bound OPT-B.C1 and OPT-A Discovery and Development parent chains passed full-byte verification and completed the bounded C2 replay.**

The operation did not consume Validation, publish a C2 release, change a selector or activate C2.

## Execution

- Workflow: `C2-G4 exact-parent market replay`
- Workflow run: `30210057332`
- Workflow source commit: `4fb06b4d2b13bdf737446cb619e548eb987aeab1`
- Result artifact: `8634383302`
- Artifact digest: `sha256:b8f993f733aed75e488aa60883f00a53596c15e5cd6c14edb787fc3bc12df62f`
- Artifact retained until: `2026-10-24T16:16:45Z`

## Parent verification

- C1 Discovery and Development: 192 record shards, 194 manifest-bound payload objects and 196 canonical objects including manifests.
- OPT-A Discovery and Development: 394 manifest-bound payload objects and 192 price files.
- C1 and OPT-A manifest identities, file inventories, byte counts and SHA-256 values: `PASS`.

## Replay result

| Role | Input records | Scopes | State records | Transition records | Rejected |
|---|---:|---:|---:|---:|---:|
| Discovery | 159,892 | 6 | 303,856 | 245,752 | 0 |
| Development | 52,872 | 6 | 100,578 | 78,158 | 0 |
| **Total** | **212,764** | **12** | **404,434** | **323,910** | **0** |

The replay produced 24 manifestable JSONL outputs totalling 872,839,722 bytes. The complete state and transition streams remain external to Git in workflow artifact `8634383302`.

## Authority retained

- Validation consumption: `LOCKED_UNCONSUMED`
- Local C2 candidate release: `NONE`
- Publication: `NONE`
- Selector: `NONE`
- Activation: `NONE`
- Probability, exposure, trading and execution: `NONE`

## Next boundary

A separate candidate-freeze and QA gate is required before any local C2 candidate release may be constructed or considered for publication or activation.

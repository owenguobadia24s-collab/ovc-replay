# RPS-G1B QA Packet

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP2`
- Gate candidate: `RPS-G1B`
- Baseline main: `6aaa898727be83ebf3e5c32ebca129d38e629adb`
- Branch: `build/rps-g1b-gapped-source-amendment`
- Tested implementation commit: `4e4c58799258f4bc87bac299affcec1c6ea57f7e`
- Tested PR merge ref: `3de50d7e1ae24fbc7f47382dba2577e740283ee0`
- Canonical workflow: `30286571687`
- Canonical unit-test job: `90045733438`
- QA state: `PASS`
- Provider network access: `false`
- External quarantine accessed by GitHub: `false`

## Review scope

QA covers only the proposed checksum-pinned, no-network recovery of the exact RPS-G1A June quarantine into a local immutable `GAPPED` source slice.

## Static findings

- Exact slice and quarantine identities are compiled into the recovery contract.
- The command has no runtime option for another quarantine, date, provider, instrument, side or clock.
- The exact observed transport sizes are pinned.
- SHA-256 values are generated locally and canonicalised in a separate recovery inventory.
- The original quarantine is re-hashed before copy, copied into new staging, verified after copy and re-hashed after evaluation.
- The source incident is not copied or relabelled into the accepted slice.
- Missing timestamps and gap runs are fully enumerated.
- Incomplete 15M, M1-derived H1 and 2H parents are listed as unavailable and an executable guard rejects their consumption.
- Gap, pairing, H1 and downstream receipts are written before the recovery pass/fail decision.
- CI and GitHub Actions freeze execution are denied before local-path resolution.
- No provider request exists in the recovery module or workflow.

## Executed test evidence

The canonical repository workflow checked out PR merge ref `3de50d7e1ae24fbc7f47382dba2577e740283ee0` containing implementation commit `4e4c58799258f4bc87bac299affcec1c6ea57f7e` and executed:

```text
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Workflow `30286571687`, job `90045733438`, completed `success`.

The discovered suite includes the new generated-BI5 RPS-G1B tests and the existing RPS-G1A/base intake regressions. The new tests cover exact GAPPED acceptance, checksum-pinned copy, source-quarantine non-mutation, checksum tamper rejection, cross-side gap mismatch rejection, QA materialisation before failure quarantine, downstream parent exclusion, executable incomplete-parent rejection, exact gate binding and CI denial.

The two added JSON schema files are syntactically valid repository artifacts. The dedicated RPS-G1B workflow also contains explicit JSON parsing, focused/regression suites and a CI freeze-denial step; the repository's canonical workflow supplied the executed gate evidence before the new workflow exists on `main`.

## Acceptance review

| Condition | QA result |
|---|---|
| Exact June slice and quarantine binding | PASS |
| 4,285/35/24 M1 invariants | PASS |
| Identical BID/ASK timestamp sets | PASS |
| Complete H1 and 64-hour exact reconciliation | PASS |
| Immutable missing-timestamp/run evidence | PASS |
| 15M/H1/2H exclusion propagation | PASS |
| Incomplete-parent executable rejection | PASS |
| Checksum tamper and copy mismatch rejection | PASS |
| QA receipts before failure quarantine | PASS |
| No provider access in implementation/tests | PASS |
| Source quarantine mutation/relabel | DENIED |
| Release/selector/R2/Validation/live authority | DENIED |

## Warnings

Actual external byte hashes are unavailable to GitHub and are not claimed by this QA packet. Local checksum generation and real quarantine re-evaluation remain operator-local work after gate approval. A passing generated fixture does not pre-approve any divergence in the real quarantine; the real command must reproduce every exact invariant.

## Recommendation

`PASS` — the code, tests, contracts, schemas, guide and programme state are consistent and non-activating. The proposed GAPPED source-integrity authority remains operator-reserved and must not be self-ratified.

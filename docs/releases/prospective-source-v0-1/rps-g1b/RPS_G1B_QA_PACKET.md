# RPS-G1B QA Packet

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP2`
- Gate candidate: `RPS-G1B`
- Baseline main: `6aaa898727be83ebf3e5c32ebca129d38e629adb`
- Branch: `build/rps-g1b-gapped-source-amendment`
- QA state: `PENDING_FINAL_CI`
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

## Required test evidence

1. Focused RPS-G1B generated-BI5 tests.
2. RPS-G1A regression tests.
3. Base bounded-intake regression tests.
4. Canonical repository unittest suite.
5. JSON schema parsing.
6. Explicit CI freeze-denial proof.

## Acceptance expectation

`PASS` requires all required tests to succeed on the final pinned PR head, no review blocker, no source or authority expansion and no unresolved discrepancy between the contract, implementation, schemas, guide, gate packet and programme registry.

## Warnings

Actual external byte hashes are unavailable to GitHub and are not claimed by this QA packet. Local checksum generation and real quarantine re-evaluation remain operator-local work after gate approval.

## Recommendation

`PENDING_FINAL_CI`. If the final candidate checks pass, recommend `PASS` for the code-and-contract packet while retaining the RPS-G1B authority decision for the operator.

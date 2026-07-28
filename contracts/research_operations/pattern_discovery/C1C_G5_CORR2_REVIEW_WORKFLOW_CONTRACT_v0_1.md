# C1C-G5-CORR2 Review Workflow Contract v0.1

## Status

`FROZEN_CANDIDATE_FOR_NONACTIVATING_IMPLEMENTATION`

## Authority source

Operator decision `C1C-G5-CORRECTIVE-PILOT-REVIEW = DEFER`, recorded on main at `8be9ded5a3f42e79d423ee06e2f890bc7cbf7d8b`.

## Purpose

Close the review-workflow and Console-context findings and permit one operator-local re-review of exactly two deferred Pilot Discovery objects from the immutable C2 v2 corrective run.

## Exact identities

- packet: `C1C-G5-CORR2`
- return gate: `C1C-G5-CORRECTIVE-PILOT-REVIEW`
- pilot run: `PD.PILOT.RUN.96c16f11717e787f971851ee`
- pilot namespace: `PD.PILOT.GBPUSD.20260622_20260625.v2`
- C2 release: `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2`
- C2 manifest: `MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1`
- selector: `SELECTOR.OPT-B.C2.GBPUSD.v2`

Only these deferred candidates may be re-reviewed:

- `PDPILOT-CANDIDATE-4f41e21b6cd075e0fdbc40e4`
- `PDPILOT-CANDIDATE-bab63b935155e4d9033aed81`

## Read-only evidence resolution

The resolver may read only:

- `review/queue-items.jsonl`
- `review/console-bundle.json`
- `derived/fingerprints.jsonl`
- `derived/cluster-versions.jsonl`
- `operator-review-v2/pilot-review-receipt-v2.json`

Every reference must use an exact allowlisted relative path and exact candidate or cluster fragment. Absolute paths, traversal, arbitrary files and unresolved identities fail closed.

The Console must show queue, candidate-detail, fingerprint, source-lineage and nearest structural-comparison status in a distinct read-only panel. Missing comparison context must be displayed as `NOT_AVAILABLE_EXPLICIT`; it may never be inferred from later outcomes.

## Operator re-review

The local finalizer may prepare and sign a new append-only `operator-review-corr2` layer. It may not overwrite the machine run, original review, structured v2 review or any existing output.

Each deferred object must receive one final disposition:

- `WORKFLOW_ACCEPTED`, or
- `REJECT_PILOT_OBJECT`.

A decision requires a `PD-CORR2-*` closure code, non-semantic decision basis, closure criteria, notes and exact resolved evidence references. A further deferred disposition is not accepted as closure.

## Required outputs

- `deferred-rereview-receipt-corr2.json`
- `c1c-g5-corr2-closure-ledger.json`
- `signed-c1c-g5-corr2-evidence-inventory.json`
- `c1c-g5-corrective-pilot-review-return-gate-input.json`

The receipt and inventory require operator-local Ed25519 SSHSIG signatures under namespace `ovc-rps`.

## Retained prohibitions

No second machine replay, provider access, canonical Discovery processing or append, semantic/family/candidate/novelty/model/threshold promotion, selector or release mutation, R2 publication, Validation consumption, probability, risk, exposure, trading, execution, autonomous processing or agent write is authorised.

## Rollback

Preserve all immutable and signed pilot evidence. Revert only CORR2 code, read-only projection, schemas and packet records through a new non-destructive commit. Never delete or rewrite an operator review layer.

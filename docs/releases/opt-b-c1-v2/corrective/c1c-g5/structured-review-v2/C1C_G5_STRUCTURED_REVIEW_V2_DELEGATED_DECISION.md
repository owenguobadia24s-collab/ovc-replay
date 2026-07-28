# C1C-G5-REVIEW-V2-CORRECTION — Delegated Decision

- **Decision:** `PASS`
- **Authority:** `DELEGATED_AUTO_EXECUTABLE`
- **Packet:** `C1C-G5-REVIEW-V2-CORRECTION`
- **Gate retained:** `C1C-G5-CORRECTIVE-PILOT-REVIEW`
- **Baseline:** `0c687101e031b404b3994c8bb96d65b177f97743`
- **Tested candidate:** `22acce012527c23e1f251c379dffd0e7b282dd5c`
- **Branch:** `build/c1c-g5-structured-v2-review`
- **Date:** `2026-07-28`

## Accepted evidence

The corrective Pilot Discovery machine run is accepted as deterministic, signed and exactly bound to:

- run `PD.PILOT.RUN.96c16f11717e787f971851ee`;
- namespace `PD.PILOT.GBPUSD.20260622_20260625.v2`;
- C2 release `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2`;
- manifest `MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1`;
- selector `SELECTOR.OPT-B.C2.GBPUSD.v2`;
- operator signing binding `RPS.SIGNING.50092c28981fef08f53a6cb5`.

All compact file hashes and all three Ed25519 SSHSIG records passed verification.

## Corrected defect

The original corrective review used the v1 finalizer and accepted five non-accepted dispositions without the structured evidence required by the already-approved v2 review contract. The packet adds a fail-closed v2 re-review path over the immutable machine run. The original signed v1 review remains preserved as superseded review evidence.

No second machine replay is required or authorised.

## Tests and QA

- Workflow `30398079249`, job `90405918618`: focused exact evidence, signatures, Pattern Discovery dependencies, complete repository tests, schemas, authority guards and CI-denial checks — `PASS`.
- Workflow `30398079004`, job `90405917808`: independent complete repository suite — `PASS`.
- QA: `PASS_IMPLEMENTATION_BLOCKED_OPERATOR_LOCAL_STRUCTURED_REVIEW`.

## Authority delta

This decision accepts only deterministic, non-activating review tooling, contracts, schemas, tests, evidence indexing and programme-state updates. It does not accept the human review findings and does not decide `C1C-G5-CORRECTIVE-PILOT-REVIEW`.

Canonical Discovery processing and append, semantic/family/candidate/threshold/model promotion, active novelty ranking, selector or release mutation, R2 publication, Validation consumption, probability, risk, exposure, trading, execution, autonomous processing and agent write remain denied or none.

## Rollback

Preserve the immutable v2 machine run and all signed v1 evidence. Revert only this implementation packet and retain `C1C-G5-BLOCK-002` and every authority denial.

## Continuation

After the eligible squash merge, complete and sign the structured v2 operator review locally. Return the four compact `operator-review-v2` files for the consolidated operator gate.

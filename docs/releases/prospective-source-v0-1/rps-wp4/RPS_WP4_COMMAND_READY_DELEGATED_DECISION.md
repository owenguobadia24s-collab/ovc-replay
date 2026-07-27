# RPS-WP4 — Delegated Command-Readiness Decision

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP4`
- Decision: `PASS_COMMAND_READY`
- Authority: `DELEGATED_AUTO_EXECUTABLE_NON_ACTIVATING_COMMAND_PREPARATION`
- Baseline main: `c8429ebdf8774a876d5a33e495cb313e31c8d034`
- Candidate branch: `build/rps-wp4-operator-signing-replay-acceptance`
- Pull request: `#110`
- Tested head: `f6ea7e9868617fc7f664fca01d2956b71b83d92f`
- Dedicated workflow: `30295366127`
- Dedicated job: `90074921791`
- Canonical workflow: `30295362965`
- Canonical job: `90074911976`
- QA: `PASS_COMMAND_READY`

## Decision

Accept the RPS-WP4 implementation as ready for operator-local execution and merge it into `main` after final-head checks pass.

The packet provides exact compute verification, external-only Ed25519 key setup, signed TIME_GATED_REPLAY acceptance and compact RPS-G4 gate-evidence preparation. It does not create a real key or acceptance in GitHub.

## Test result

The dedicated workflow passed:

- focused RPS-WP4 tests;
- canonical repository tests;
- CI denial of operator key generation;
- CI denial of signed replay acceptance.

The repository-wide canonical workflow also passed.

## Authority assessment

This decision creates no operator-reserved authority. The implementation remains fail-closed with:

- active binding `null`;
- ACTIVE_RESEARCH_TRIAGE false;
- LIVE_PROSPECTIVE append `DENIED`;
- write authority false;
- release status `NOT_A_RELEASE`;
- selector eligibility `NONE`;
- R2 and Validation `DENIED`;
- probability, risk, exposure, trading, execution and agent-write authority `NONE`.

The next authority boundary is RPS-G4, which requires explicit operator approval before the exact binding may be activated for ACTIVE_RESEARCH_TRIAGE or PD-WP5 first LIVE_PROSPECTIVE operation.

## External boundary

RPS-WP4 remains `RUNNING` after command merge until the operator locally:

1. re-verifies all source and compute bytes;
2. creates the external Ed25519 key;
3. protects the private key with restrictive OS permissions;
4. signs and verifies the replay acceptance;
5. supplies the four compact RPS-G4 evidence files.

## Rollback

Revert the bounded command packet while preserving all external source, compute, key, signed-candidate and quarantine artifacts. No key deletion, signature rewrite, artifact mutation or force-push is authorised.

# RPS-WP4 — Command Merge Receipt

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP4`
- Pull request: `#110`
- Final command-ready head: `810a0fd88b320a36a56a26f071cd60ccf48bde4f`
- Initial dedicated workflow: `30295366127`
- Initial dedicated job: `90074921791`
- Initial canonical workflow: `30295362965`
- Initial canonical job: `90074911976`
- Final dedicated workflow: `30295472130`
- Final dedicated job: `90075271918`
- Final canonical workflow: `30295472528`
- Final canonical job: `90075272421`
- Squash merge: `f453d7260d15720a4741a14684ec0e1a61e67a3e`
- QA: `PASS_COMMAND_READY`
- Merged on: `2026-07-27`

## Result

The exact operator-local RPS-WP4 command is present on `main`. It can re-verify the full accepted compute run, create one external Ed25519 key, require operator confirmation of restrictive OS permissions, sign and verify one TIME_GATED_REPLAY acceptance candidate and prepare compact RPS-G4 evidence.

RPS-WP4 remains `RUNNING`. No operator key, signed acceptance, active binding, LIVE_PROSPECTIVE append or write authority was created by GitHub.

## Continuation

The operator must run:

1. `preflight`;
2. `setup-key`;
3. restrictive Windows private-key permissions and review;
4. `accept-replay -ConfirmPrivateKeyProtected`;
5. upload exactly four compact JSON files.

## Next gate

`RPS-G4` is operator-required. Its proposed authority delta is:

`ACTIVATE_EXACT_BINDING_FOR_ACTIVE_RESEARCH_TRIAGE_AND_ENABLE_PD_WP5_FIRST_LIVE_PROSPECTIVE_OPERATION`

Until that gate is explicitly approved:

- active binding remains `null`;
- ACTIVE_RESEARCH_TRIAGE remains false;
- LIVE_PROSPECTIVE append remains `DENIED`;
- write authority remains false;
- PD-WP5 remains blocked.

## Rollback

Revert the RPS-WP4 command merge and this receipt while preserving all external source, compute, key, signed-candidate and quarantine artifacts. No automated key deletion, signature rewrite, external mutation or history rewrite is authorised.

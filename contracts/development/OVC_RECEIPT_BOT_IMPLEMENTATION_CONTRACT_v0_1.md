# OVC Receipt-Bot Bounded Implementation Contract v0.1

## Authority

DA-G4 operator decision `DA-G4.OPERATOR.PASS.20260801T172600Z` authorises implementation inside `NARROW_REPOSITORY_BOT_PROPOSAL_BRANCH_WRITE_FOR_DEVELOPMENT_ACCELERATION_RECEIPTS_ONLY`.

The current state is `APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE`. No credential is provisioned and no repository write authority is active. This contract does not activate the capability.

## Approved action surface

After every activation condition passes, an injected repository adapter may expose only:

1. `CREATE_BOT_BRANCH` for `bot/ovc-dev-accel-receipts/*` from an exact lawful `main` SHA;
2. `CREATE_OR_UPDATE_ALLOWLISTED_FILES` on that bot branch;
3. `OPEN_OR_UPDATE_PULL_REQUEST` from that branch to `main`.

The implementation contains no merge, approval, review-dismissal, deletion, force-push, history-rewrite or direct-main method.

## Exact path boundary

Only these paths are eligible:

- `docs/releases/development-acceleration-v0-1/**`
- `registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json`
- `registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml`

Unknown, ambiguous, absolute, traversal, duplicate or normalized-outside paths block.

## Immutable work packet

Each attempted proposal must bind the approved profile identity and hash, exact source and current `main` SHAs, approved bot branch, target paths and content hashes, PASS closure, PASS QA, PASS decision, reserved authority delta `NONE`, zero blockers, zero warnings, zero unresolved reviews, non-destructive rollback and a frozen idempotency key.

A stale `main` SHA, changed logical plan under an existing idempotency key or missing field blocks. An exact retry produces `IDEMPOTENT_RETRY` and may not create a second logical receipt.

## Credential and audit controls

Credentials, tokens, private keys and bearer values are prohibited in repository records, fixtures and audit output. Audit data is recursively redacted before identity calculation. The adapter receives content hashes rather than credentials or arbitrary authority data.

Each successful execution emits one deterministic audit event recording only the approved action classes. It records that merge, approval and force-push were not performed.

## Activation conditions

All conditions in `OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_POLICY_v0_1.json` must be `PASS`. In particular, activation requires independently reproducible evidence that `main` branch protection denies bot bypass and that a real proposal-branch shadow succeeded using the dedicated revocable identity.

Static implementation or unit tests cannot substitute for those external controls. Missing branch-protection evidence or missing real shadow evidence leaves activation `BLOCK` and authority inactive.

## Revocation and rollback

Revocation is independent of code rollback: keep the profile inactive or disable it, revoke the dedicated identity, prevent new bot branches and PR updates, close unmerged bot PRs if required, and revert the bounded implementation through a new non-destructive commit. Accepted records and history are preserved.

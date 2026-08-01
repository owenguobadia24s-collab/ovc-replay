# OVC Repository Receipt-Bot Authority Proposal v0.1

## Status

`PROPOSED_PENDING_OPERATOR_DA_G4`. This document grants no active authority. Repository-bot write remains `DENIED` until the operator records an explicit DA-G4 PASS and the post-decision implementation packet satisfies every condition below.

## Purpose

Remove repetitive one-purpose closure and merge-receipt administration without granting a bot authority over model code, market evidence, workflows, approvals or merges.

## Proposed authority delta

`NARROW_REPOSITORY_BOT_PROPOSAL_BRANCH_WRITE_FOR_DEVELOPMENT_ACCELERATION_RECEIPTS_ONLY`

The bot may, after all preconditions pass:

1. create a new branch matching `bot/ovc-dev-accel-receipts/*` from an exact lawful `main` SHA;
2. create or update only the allowlisted Development Acceleration court-record files on that branch;
3. open or update one pull request from that branch to `main`;
4. attach the exact closure proposal, tests, QA, decision, rollback and merge-receipt evidence to that pull request.

It may not approve or merge the pull request.

## Exact path allowlist

- `docs/releases/development-acceleration-v0-1/**`
- `registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json`
- `registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml`

No wildcard outside those roots is implied. A path that is unknown, ambiguous, normalized differently or outside the allowlist blocks the operation.

## Mandatory preconditions

Every proposed write must bind an immutable bot work packet containing:

- approved authority-profile ID and hash;
- exact source `main` SHA and unique bot branch;
- exact target paths and canonical content hashes;
- DA-WP4 closure proposal PASS;
- packet QA PASS and decision PASS;
- passing stable-head required checks;
- zero blockers, zero warnings and zero unresolved review threads;
- reserved authority delta `NONE` for the underlying packet;
- non-destructive rollback and independent revocation evidence;
- idempotency key proving that retry cannot create a second logical receipt.

A missing, stale or contradictory field blocks. The bot may not repair the packet silently.

## Permanent denials

The bot may never:

- write directly to `main` or any non-bot branch;
- merge, squash, rebase, approve or dismiss reviews;
- force-push, rewrite history, delete branches or delete accepted records;
- modify `.github/**`, source code, scripts, contracts, schemas, fixtures or tests;
- alter market, provider, release, selector, Validation, probability, risk, exposure or execution artifacts;
- alter its own authority profile, allowlist, credentials, revocation settings or gate decision;
- self-approve, broaden scope, waive a check or convert WARN/BLOCK into PASS;
- publish to R2, access providers, create releases or activate deferred capabilities.

## Repository and credential controls

The implementation must use a dedicated revocable identity with only repository contents and pull-request permissions needed for the proposal-branch workflow. Workflow, administration, secrets, environments and actions permissions remain absent. Branch protection must independently prohibit direct `main` writes and bot bypass. Application-level path and branch allowlists remain mandatory because repository content permission alone is not a native path sandbox.

No credential, token, installation ID or private key may be stored in Git, fixtures, logs, gate packets or generated receipts.

## Audit and idempotency

Every attempted action emits an append-only audit record before any proposal branch is considered complete. Identical packet identity must produce the same logical branch plan and court-record hashes. A retry may update the same bot PR only when the exact source `main` SHA and packet identity are unchanged; otherwise it blocks and requires a new packet.

## Revocation and rollback

Revocation is independent of code rollback:

1. disable the authority profile;
2. revoke or suspend the dedicated repository identity;
3. prevent creation or update of bot branches and PRs;
4. close unmerged bot PRs if required, without deleting accepted records or rewriting history;
5. revert the bounded bot-enablement merge through a new non-destructive commit.

Previously merged receipts remain court records. Revocation grants no deletion authority.

## Post-approval implementation boundary

An operator DA-G4 PASS authorises bounded implementation and eventual activation only inside this exact envelope. The post-decision profile state is `APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE`; approval does not itself activate repository-bot write authority. Activation remains conditional on:

- a closed authority-profile schema and active profile whose hash matches this proposal;
- a branch/path-enforcing writer adapter with no merge API;
- denied-action, token-redaction, idempotency, collision and revocation tests;
- verification that `main` branch protection does not allow bot bypass;
- a real proposal-branch shadow run that writes no market or code path;
- final-head complete repository assurance and QA PASS.

Failure of any condition leaves repository-bot write `DENIED`; no second authority expansion is inferred.

# OVC Receipt-Bot Pre-Activation Shadow Contract v0.1

## Purpose

This contract resolves the DA-G4B sequencing defect in which a real proposal-branch shadow was required before activation while the normal execution function correctly refused all writes until activation.

The correction creates one separate `PRE_ACTIVATION_SHADOW` route. It does not change the approved production action surface and does not activate repository-bot authority.

## Preconditions

A shadow may begin only when every DA-G4B activation condition except the two conditions produced by the shadow sequence has passed:

- `REAL_PROPOSAL_BRANCH_SHADOW_PASS` is produced only after the real shadow completes;
- `QA_PASS` is produced only after the resulting shadow evidence and final-head assurance are reviewed.

All other conditions must already be `PASS`, including `MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED`.

## Dedicated identity

The shadow must use one dedicated, independently revocable GitHub App installation identity. Its exact repository permissions are:

- Contents: write;
- Pull requests: write;
- Metadata: read.

No additional repository permission is accepted. The operator connector, a personal access token and the normal ChatGPT GitHub connector cannot substitute for the dedicated identity. Private keys and installation tokens never enter Git, fixtures, audit records, PR comments or gate packets.

## Exact shadow action surface

The shadow may perform exactly three action classes:

1. create one branch under `bot/ovc-dev-accel-receipts/*` from the exact current lawful `main` SHA;
2. write one hash-bound JSON receipt below `docs/releases/development-acceleration-v0-1/da-wp4b-shadow/`;
3. open one unmerged PR from that branch to `main`.

The branch name and PR title must explicitly identify `DA-G4B` and `shadow`. The work packet must use a new idempotency key and bind the exact target content SHA-256.

## Permanent denials

The shadow route contains no merge, approval, review dismissal, direct-main write, deletion, force-push, history rewrite, workflow mutation, authority-profile mutation, provider, R2, release, selector, Validation, market, semantic, probability, risk, exposure or execution operation.

The shadow audit must state:

- `authority_active=false`;
- `production_transport_active=false`;
- `merge_performed=false`;
- `approval_performed=false`;
- `force_push_performed=false`;
- `history_rewrite_performed=false`.

## Evidence and completion

A passing shadow produces a credential-redacted audit containing the GitHub App identity metadata, installation ID, exact source `main` SHA, branch, target path, content SHA-256, resulting commit, PR number, ruleset-evidence hash and explicit denied-action results.

The shadow PR remains unmerged. Passing the shadow does not itself activate the bot. DA-G4B may move to PASS only after the shadow evidence, final-head tests, zero warnings, zero unresolved reviews, revocation procedure and QA recommendation all pass.

## Rollback

Keep the approved profile inactive, revoke the GitHub App installation or key, close the unmerged shadow PR if required, preserve its audit evidence and revert only the bounded corrective implementation through a new non-destructive commit.

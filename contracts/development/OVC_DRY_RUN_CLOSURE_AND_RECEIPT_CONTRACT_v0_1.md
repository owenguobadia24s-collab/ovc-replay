# OVC Dry-Run Closure and Receipt Contract v0.1

## Authority

`DRY_RUN_CLOSURE_AND_RECEIPT_COMPARISON_ONLY`. The service evaluates a frozen pull-request snapshot, proposes an eligible squash-merge closure record, constructs a post-merge receipt proposal from a supplied merge SHA and compares that proposal with a manual reference receipt. It performs no GitHub write, merge, branch creation, commit, push, review dismissal, selector mutation, publication or market computation.

Repository-bot write remains `DENIED` until a separate operator PASS at DA-G4. Direct writes to `main`, force-push and history rewriting remain prohibited permanently.

## Frozen inputs

A closure snapshot must bind:

- plan, programme, packet and gate identities;
- pull-request number, `main` base, baseline commit, bounded head branch and exact head SHA;
- normalized changed-file inventory;
- passing required workflow runs;
- PASS QA and decision records;
- zero blockers, warnings and unresolved review threads;
- wholly non-reserved authority delta;
- non-destructive rollback and next packet;
- the approved closure policy ID and hash.

Missing or contradictory fields block. Chat claims and mutable live state are not inputs.

## Eligibility rules

A closure proposal is PASS only when:

1. the base branch is exactly `main`;
2. baseline and head are distinct 40-character lowercase Git SHAs;
3. the head branch matches the policy allowlist and is not `main`;
4. every changed file is repository-relative and matches an allowed policy path;
5. all required tests are PASS and uniquely identified;
6. QA status is PASS and decision is PASS;
7. reserved authority delta is `NONE`;
8. blockers, warnings and unresolved review count are zero;
9. rollback is non-destructive and does not request deletion, force-push or history rewrite;
10. merge method is `squash` and exact-head pinning remains required.

Unknown or ambiguous paths block; they do not escalate into automatic write authority.

## Receipt proposal

After a separately authorised squash merge has occurred, a supplied exact merge SHA may be used to construct a compact receipt proposal. The proposal binds the approved head, merge SHA, PR, decision, tests, authority delta, rollback and next packet. It cannot cause or imply the merge.

## Comparison

The shadow programme compares the generated proposal with a manually prepared reference receipt. Material fields must be byte-logically equal after canonical ordering. PASS requires zero material differences. Any missing, extra or unequal material field blocks. Comparison ignores no authority, identity, test or rollback field.

## No-write assurance

Every closure, receipt and comparison result records:

- `writes_performed: false`;
- `merge_performed: false`;
- `repository_bot_write: DENIED`;
- `direct_main_write: DENIED`;
- `force_push: DENIED`.

## Gate sequence

DA-G4A may auto-ratify the deterministic shadow service and comparison evidence. DA-G4 is separate and operator-required because it would grant narrow repository-bot branch-write authority. DA-G4A PASS does not grant that authority.

## Rollback

Stop generating closure proposals or revert the bounded DA-WP4 merge through a new non-destructive commit. Preserve shadow comparisons, incidents and manual receipts. Manual operator closure remains authoritative.

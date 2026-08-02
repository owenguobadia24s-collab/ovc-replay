# OVC Development Acceleration Default Workflow Adoption Proposal v0.1

## Identity

- **contract_id:** `OVC-DEV-ACCEL-DEFAULT-WORKFLOW-ADOPTION-PROPOSAL.v0.1`
- **programme_id:** `OVC-DEV-ACCEL-v0.1`
- **plan_id:** `OVC-DEV-ACCEL-IMPLEMENTATION-PLAN-0.1`
- **gate_id:** `DA-G6`
- **status:** `PENDING_OPERATOR_DA_G6`
- **active:** `false`

## Purpose

DA-G6 is the operator-reserved decision on whether the completed Development Acceleration mechanics become the default execution workflow for eligible future OVC implementation packets and whether duplicated mechanics lose active authority.

This proposal records the exact delta. It does not activate the default workflow and does not retire any authority before an explicit operator PASS.

## Proposed default workflow

For a future packet to use the default workflow, all of the following must be true:

1. an approved governing plan and machine-readable packet registry exist;
2. the packet is inside its approved authority envelope;
3. an exact packet profile identifies prerequisites, reads, writes, tests, QA, gate class and rollback;
4. universal artifact preflight passes before expensive work;
5. deterministic tiered test selection is used, with complete final-head assurance retained;
6. closure records are generated from immutable packet, QA, decision and merge inputs;
7. repository receipt writes, when used, remain limited to the active DA-G4B proposal-branch profile;
8. compact evidence export, when used, remains local, copy-only and outside the repository;
9. operator-reserved deltas continue to stop at one consolidated decision gate;
10. only eligible non-reserved PASS gates may be delegated-ratified and squash-merged automatically.

## Proposed retirement

The following duplicated mechanics would become `RETIRED_NON_AUTHORITATIVE` for future eligible packets:

- ad hoc packet-state tracking outside the programme registry;
- manually assembled merge receipts when deterministic closure inputs are available;
- unregistered changed-file test selection;
- packet execution that bypasses universal preflight;
- duplicated programme-specific copies of shared identity, preflight, test-selection, closure or compact-export mechanics.

Retirement is non-destructive. Historical files, decisions, releases, tests and evidence remain preserved. No file deletion, branch deletion, force-push or history rewrite is authorized. A programme-specific mechanic remains authoritative when its governing plan explicitly requires it or no approved default adapter exists.

## Permanent denials

DA-G6 does not grant:

- direct writes to `main`;
- merge, approval or review-dismissal authority to the receipt bot;
- force-push, history rewrite or accepted-record deletion;
- provider access, R2 write or release publication;
- selector, semantic, threshold, model, family, candidate or theory promotion;
- ACTIVE_DISCOVERY, ACTIVE_DEVELOPMENT or ACTIVE_VALIDATION;
- new instruments, markets, clocks, sides or dependencies;
- probability, risk, exposure or execution authority;
- agent write authority outside the already approved receipt-proposal profile.

## Activation conditions

A PASS may be implemented only after:

- DA-WP1 through DA-WP5 and DA-G4/DA-G4B are completed and merged;
- all required checks and QA pass on the DA-G6 gate head;
- the exact proposed profile remains closed and inactive before decision;
- the retirement inventory is explicit and non-destructive;
- rollback restores the prior programme-specific workflow without deleting accepted records;
- no unresolved review, warning or blocker remains.

## Decisions

Allowed operator decisions are `PASS`, `DEFER`, `BLOCK`, `QUARANTINE` or `SUPERSEDE`.

A PASS authorizes implementation of the exact default workflow and non-destructive authority retirement described here. Any broader delta requires another operator gate.

## Rollback

Disable the default profile, restore programme-specific workflow selection, mark retired mechanics active again where still valid, revoke no historical evidence and make all changes through new non-destructive commits. Preserve the DA-G4B receipt-bot constraints and DA-WP5 copy-only exporter constraints.

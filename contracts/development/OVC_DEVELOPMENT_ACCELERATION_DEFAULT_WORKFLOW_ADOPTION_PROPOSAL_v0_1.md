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

## Mandatory acceleration conditions

DA-G6 PASS is conditional on all five controls below. They are part of the proposed authority envelope, not optional later improvements.

### 1. Sealed candidate and two-phase gate protocol

A packet moves through `IMPLEMENTED -> QA_REVIEW -> CANDIDATE_SEALED -> OPERATOR_DECISION_PENDING -> MERGED -> RECEIPT_RECORDED`. The sealed candidate is an exact immutable commit. No implementation, evidence, run-ID, PR-number, decision or receipt mutation may be committed to that candidate after sealing. An operator decision must bind the exact candidate SHA and is rejected if the pull-request head moves. Decision and merge evidence are written after the decision through the separately governed receipt/control path.

### 2. Atomic Git transaction and two-head mutation budget

A coherent packet update uses one blob/tree/commit transaction and one fast-forward branch update. Before candidate seal, a packet may use at most two candidate-head mutations: one coherent candidate and one corrective candidate. After candidate seal, the permitted mutation count is zero. Further technical repair supersedes the unsealed candidate through a new bounded branch; accepted history is preserved.

### 3. One-active-PR programme lease

Each programme has at most one active continuation PR. A predecessor packet, gate or receipt PR must be merged, closed as `SUPERSEDED_PRESERVED`, or explicitly recorded as a non-blocking historical exception before the next permanent continuation PR becomes eligible for candidate seal. The lease records programme, packet, branch, PR, state and predecessor resolution.

### 4. Required-check provenance and ruleset-health preflight

Before branch creation, after any workflow or ruleset change, and before merge, a reproducible ruleset-health check must verify the ruleset ID and hash, required context, workflow path/name/job, expected GitHub App or check-suite source, event type, branch pattern and verification time. A successful Actions run whose source identity does not satisfy branch protection is a blocker, not a PASS.

### 5. One canonical required PR runtime

All ruleset-required PR assurance uses one registered runtime. The initial canonical runtime is `ubuntu-latest` with CPython `3.11`. Additional-version compatibility runs are scheduled, manually dispatched or release-specific and do not create duplicate required full-suite checks unless a governing plan explicitly requires them.

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
- all five mandatory acceleration conditions are represented in the profile, schema, QA and tests;
- the predecessor continuation/receipt state is resolved or explicitly recorded under the one-active-PR lease;
- the retirement inventory is explicit and non-destructive;
- rollback restores the prior programme-specific workflow without deleting accepted records;
- no unresolved review, warning or blocker remains.

## Decisions

Allowed operator decisions are `PASS`, `DEFER`, `BLOCK`, `QUARANTINE` or `SUPERSEDE`.

A PASS authorizes implementation of the exact default workflow, the five mandatory acceleration controls and non-destructive authority retirement described here. Any broader delta requires another operator gate.

## Rollback

Disable the default profile, restore programme-specific workflow selection, mark retired mechanics active again where still valid, revoke no historical evidence and make all changes through new non-destructive commits. Preserve the DA-G4B receipt-bot constraints and DA-WP5 copy-only exporter constraints.

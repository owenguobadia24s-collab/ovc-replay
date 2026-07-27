# PD-WP5 — First LIVE_PROSPECTIVE Operation Blocker QA

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `PD-WP5`
- Baseline main: `5842c8e9079efb82e5dc78dbeba31005c27eaa24`
- Branch: `build/pd-wp5-first-live-prospective-operation`
- Tested gate-ready head: `9694f279ba2ca64d85c77e8679a863c6a79f2be3`
- Focused workflow: `30302750156`, job `90099418472` — PASS
- Canonical workflow: `30302750032`, job `90099417677` — PASS
- QA recommendation: `BLOCK_PENDING_RPS_G4A`

## Finding

RPS-G4 lawfully activated:

- source binding `RPS.BINDING.32fb3003efa072916c11e907`;
- signing binding `RPS.SIGNING.50092c28981fef08f53a6cb5`;
- operator `OVC.OPERATOR.PRIMARY.LOCAL.V1`;
- one bounded PD-WP5 LIVE_PROSPECTIVE operation.

The activation cutoff is the Git committer timestamp of merge `aa29b23a7a83e33880ac2d80deb013f0c0390f30` on 27 July 2026. The exact active source binding has `eligible_data_through_utc = 2026-06-25T00:00:00Z`.

No candidate can simultaneously:

1. be strictly after activation;
2. use the exact active binding; and
3. remain inside that binding's eligible market-data coverage.

The first operation is therefore blocked by source coverage before trigger, fingerprint, clustering, queue or review logic can run.

## Diagnostic implementation

The packet adds a no-network operator-local preflight that:

- requires clean local `main` containing the activation merge;
- derives the cutoff from Git;
- validates exact activation authority;
- compares binding coverage to the cutoff;
- rejects replay and pre-activation candidate packages;
- emits a compact blocker and exact RPS-G4A proposal;
- performs no provider request and no canonical append.

Expected current result:

`BLOCKED_POST_ACTIVATION_SOURCE_REQUIRED`

## Tests

The focused workflow passed:

- source-coverage contradiction reproduction;
- exact RPS-G4A scope;
- strict post-activation chronology;
- replay and pre-activation rejection;
- exact source/signing/operator binding checks;
- no-network preflight;
- unapproved gate and provider-request denial;
- retained authority prohibitions.

The canonical repository suite also passed. No unresolved implementation defect remains.

## Prohibited workarounds

QA rejects:

- relabelling the June TIME_GATED_REPLAY output;
- using June source IDs for a July trigger;
- manually entering source IDs;
- changing or rounding the activation cutoff;
- synthesising or extrapolating market data;
- deriving native H1 as a substitute for the required provider stream;
- creating a zero-evidence or fixture batch and calling it prospective.

## Smallest lawful resolution

Prepare one operator amendment, `RPS-G4A`, for:

- slice `RPS.DUKASCOPY.GBPUSD.20260728_20260801.v1`;
- interval `[2026-07-28T00:00:00Z, 2026-08-01T00:00:00Z)`;
- M1 BID, M1 ASK, native H1 BID, native H1 ASK;
- 25 MiB compressed / 100 MiB expanded limits;
- external-artifact root only;
- no provider request before approval;
- no provider access in CI;
- execution deferred until the July 2026 native-H1 BI5 objects are available.

After intake, the programme must freeze and QA the exact source, run deterministic 15M/2H OPT-A→C1→C2 processing, create a new exact post-activation binding, execute one PD-WP5 operation and stop at PD-G5.

## Current authority

ACTIVE_RESEARCH_TRIAGE remains approved and fail-closed. Candidate append remains disabled. The blocker does not revoke RPS-G4 and does not grant a new provider request.

## Retained denials

Canonical append, automatic evidence creation, autonomous processing, active novelty ranking, semantic promotion, C2E/C2.5/C3, selector/release/R2 mutation, Validation, probability, risk, exposure, trading, execution and agent writes remain denied.

## Rollback

Revert the diagnostic and blocker packet while preserving RPS-G4 activation, source, compute, keys, signatures and quarantines. Do not weaken the cutoff or replay exclusions.

## Recommendation

`BLOCK_PENDING_RPS_G4A`.

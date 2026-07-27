# PD-WP5 — Blocker and RPS-G4A Gate Merge Receipt

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `PD-WP5`
- Decision: `BLOCK`
- Decision authority: `DELEGATED_DIAGNOSTIC_AND_STATE_RECORD_ONLY`
- Pull request: `#115`
- Final head: `17f052c8cda7a3681a538cbf57973f3e96fa60fa`
- Squash merge: `ae60a9a7d7778dc92ef802d1492ba7a896a11923`
- Focused workflow: `30302940477`, job `90100070018` — PASS
- Canonical workflow: `30302940354`, job `90100069185` — PASS
- QA: `BLOCK_PENDING_RPS_G4A`

## Result

The no-network PD-WP5 preflight, source-coverage blocker, delegated BLOCK decision and consolidated RPS-G4A gate packet are present on `main`.

The exact active source binding remains `RPS.BINDING.32fb3003efa072916c11e907`, but its eligible market data ends at `2026-06-25T00:00:00Z`. A genuine LIVE_PROSPECTIVE candidate must be strictly after activation merge `aa29b23a7a83e33880ac2d80deb013f0c0390f30`. PD-WP5 is therefore blocked before trigger, candidate, queue or append execution.

## Current authority

RPS-G4 ACTIVE_RESEARCH_TRIAGE remains approved and fail-closed. Candidate source resolution and live append remain false. Provider access, canonical append, replay substitution and every broader authority remain denied.

## Operator boundary

The next gate is `RPS-G4A`, proposing exactly one post-activation Dukascopy slice:

- `RPS.DUKASCOPY.GBPUSD.20260728_20260801.v1`;
- `[2026-07-28T00:00:00Z, 2026-08-01T00:00:00Z)`;
- M1 BID/ASK and native H1 BID/ASK;
- 25 MiB compressed / 100 MiB expanded;
- external-artifact root only;
- no provider request until operator approval and native-H1 availability.

Recommended decision: `DEFER` until the July native-H1 monthly objects are available. A `PASS` may record exact authority now, but execution must still fail closed until the availability condition is met.

## Rollback

Revert the diagnostic and gate-preparation merge while preserving RPS-G4 activation, source, compute, key, signature, rejected requests and quarantine artifacts. Do not weaken chronology or replay exclusions.

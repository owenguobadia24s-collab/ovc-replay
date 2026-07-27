# RPS-G4 — Activation Merge Receipt

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-G4-ACTIVATION`
- Governing gate: `RPS-G4`
- Decision merge: `b52fa297faa1b593fe9aaaf5d36a1b4e39a50eac`
- Pull request: `#113`
- Final head: `1069fc48b1a8c2151cfc5d9bd90c22b4d1e7c78b`
- Activation merge: `aa29b23a7a83e33880ac2d80deb013f0c0390f30`
- Activation workflow: `30301305760`, job `90094638739` — PASS
- Canonical workflow: `30301305716`, job `90094638639` — PASS
- QA: `PASS_ACTIVATION`

## Effective authority

The exact RPS-G4 source and signing bindings are effective on `main` for one bounded PD-WP5 LIVE_PROSPECTIVE operation. ACTIVE_RESEARCH_TRIAGE is enabled, but candidate append remains disabled until a new LIVE_PROSPECTIVE candidate resolves immutable source lineage.

The strict admissibility cutoff is the Git committer timestamp of activation merge `aa29b23a7a83e33880ac2d80deb013f0c0390f30`. The PD-WP5 command must resolve that timestamp locally from Git and require `trigger_first_valid_at` to be strictly later.

## Retained denials

Replay backfill, automatic evidence creation, autonomous processing, active novelty ranking, semantic promotion, C2E/C2.5/C3, selector/release/R2 mutation, Validation, probability, risk, exposure, trading, execution and agent writes remain denied.

## Continuation

The next packet is `PD-WP5`. Its first operation is limited to one and must stop at `PD-G5` with complete evidence, or at a concrete external-artifact blocker.

## Rollback

Disable triage, clear exact bindings, deny append and stop PD-WP5 while preserving all source, compute, keys, signatures, rejected requests, append-only evidence, audits and quarantines.

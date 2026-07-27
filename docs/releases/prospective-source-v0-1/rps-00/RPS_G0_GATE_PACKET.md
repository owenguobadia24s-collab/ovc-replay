# RPS-G0 — Enablement Design Acceptance

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- Baseline: `979aa574a2b29e2f298ee3718c8cbc3588c6a813`
- Packet: `RPS-00`
- Branch: `build/rps-00-prospective-source-freeze`
- Current authority: PD-G4 approved bounded human review and governed append bridge; no live source or live triage.
- Proposed delta: repository reconciliation and fixture-only prospective-source foundation authority.

## Completed work

1. Reconciled PD-WP4 as completed at merge `979aa574a2b29e2f298ee3718c8cbc3588c6a813`.
2. Registered the ratified RPS programme, packets, operator gates and prohibitions.
3. Added a typed fail-closed `AuthoritySnapshot`.
4. Replaced hard-coded UI gate text with runtime authority state while keeping live append disabled by default.
5. Added authority tests proving PD-G4 alone, replay mode, missing key, unhealthy bridge, missing source binding or absent RPS-G4 cannot enable live append.

## Acceptance conditions

- No provider request or provider byte access: PASS.
- No live processing or LIVE_PROSPECTIVE count: PASS.
- No selector, release, R2 or Validation mutation: PASS.
- Novelty remains baseline/shadow only: PASS.
- Semantic, C2E/C2.5/C3, OPT-C/D and exposure authority remain denied: PASS.
- Rollback is disable-only and preserves PD-G4 artifacts: PASS.

## QA recommendation

PASS. The delta is non-activating, inside the ratified plan and auto-ratifiable. Continue to RPS-WP1. Stop before RPS-G1 real-provider intake.

## Rollback

Revert the RPS-00 merge. Runtime defaults return to disabled; no source, evidence, selector, release or remote object is affected.

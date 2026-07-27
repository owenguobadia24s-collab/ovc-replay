# RPS-G1 — Real Provider Intake Authorisation

## Decision requested

Authorise one bounded local Dukascopy GBP/USD source intake. This gate does **not** activate Pattern Discovery triage, LIVE_PROSPECTIVE evidence, a selector, a release, R2 publication or Validation consumption.

## Programme state

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1, ratified.
- Completed packets: RPS-00; RPS-WP1 candidate complete with canonical repository tests passing.
- Baseline main: `c54c4246c1976a9a9aa75fe2d1307f0955b4865d`.
- Candidate branch: `build/rps-wp1-source-fixture-foundation`.
- Current authority: fixture and non-provider prospective computation only.
- Proposed delta: one exact local provider request and immutable source-slice freeze.

## Exact proposed intake

| Field | Proposed value |
|---|---|
| Provider | Dukascopy |
| Instrument | GBP/USD |
| Source window | `[2026-07-24T00:00:00Z, 2026-07-27T00:00:00Z)` |
| Detailed objects | M1 BID and M1 ASK |
| Reconciliation controls | native H1 BID and native H1 ASK |
| Destination | `%OVC_EXTERNAL_ARTIFACT_ROOT%/prospective-source/intake/RPS.DUKASCOPY.GBPUSD.20260724_20260727.v1/` |
| Network method | operator-local provider adapter; no credential or network access in CI |
| Request bound | exactly four logical streams for the stated interval; no rolling backfill |
| Storage bound | abort before freeze if compressed bytes exceed 25 MiB or expanded workspace exceeds 100 MiB |
| Result identity | `RPS.DUKASCOPY.GBPUSD.20260724_20260727.v1` if all integrity checks pass |

## Acceptance conditions after intake

1. Provider, instrument, side, interval and schema fingerprints resolve exactly.
2. Every source object has byte size and SHA-256 recorded.
3. Ordering, duplication, gap, BID/ASK and native-H1 reconciliation checks complete.
4. No gap is filled or repaired.
5. The frozen slice is local-only, `NOT_A_RELEASE`, selector-ineligible and R2-denied.
6. Raw source bytes, provider credentials and machine paths remain outside Git.
7. Any limit breach, source mismatch or integrity failure leaves the mutable workspace quarantined and creates no accepted source slice.

## Tests and QA

RPS-WP1 covers deterministic 15M/2H parent construction, admissible-cutoff rejection, gap quarantine, replay-only C1/C2 projection, source binding and cursor restart idempotency. Canonical repository unittest CI passed on the packet branch. QA recommends PASS for the fixture foundation and requests operator authority only for the exact intake above.

## Warnings and unresolved matters

- No real provider request has occurred.
- Actual provider object byte size is unknown until response headers/bytes are received; the hard bounds above force an abort rather than scope expansion.
- Provider corrections or gaps require quarantine and a later decision; they cannot be silently repaired.
- The operator must ensure `OVC_EXTERNAL_ARTIFACT_ROOT` points to an available local external-artifact root before execution.

## Authority retained as denied

ACTIVE_RESEARCH_TRIAGE, LIVE_PROSPECTIVE append, selector/release/R2 mutation, Validation, active novelty ranking, semantic/archetype promotion, C2E/C2.5/C3, OPT-C/OPT-D, probability, risk, exposure, trading, execution and agent write.

## Rollback

Stop the intake adapter. Delete only the mutable incomplete workspace. Preserve any already-frozen checksum-addressed source object and incident record. Revert no historical release and mutate no selector.

## Recommended decision

**PASS** the exact bounded intake above, or **DEFER** with a replacement half-open UTC interval/storage bound. After PASS, execute RPS-WP2 through RPS-WP4 continuously and stop at RPS-G4.

## Exact command

`OVC APPROVE RPS-G1`

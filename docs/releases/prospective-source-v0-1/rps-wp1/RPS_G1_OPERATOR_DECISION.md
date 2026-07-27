# RPS-G1 — Operator Decision

- Decision: **PASS**
- Authority: `OPERATOR`
- Approval command: `OVC APPROVE RPS-G1`
- Approved on: `2026-07-27`
- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Gate packet: `docs/releases/prospective-source-v0-1/rps-wp1/RPS_G1_OPERATOR_GATE_PACKET.md`
- Baseline main: `e893a026606a56fca1e746433d693ab86f7c3cb5`

## Approved authority delta

One bounded, operator-local Dukascopy GBP/USD intake for the half-open interval `[2026-07-24T00:00:00Z, 2026-07-27T00:00:00Z)`, consisting only of M1 BID, M1 ASK, native H1 BID and native H1 ASK, with the storage and integrity limits frozen in the gate packet.

## Conditions

1. Destination remains `%OVC_EXTERNAL_ARTIFACT_ROOT%/prospective-source/intake/RPS.DUKASCOPY.GBPUSD.20260724_20260727.v1/` outside Git.
2. Abort before freeze above 25 MiB compressed or 100 MiB expanded.
3. No gap filling, interpolation, repair or interval expansion.
4. Any mismatch or integrity failure quarantines the mutable workspace and creates no accepted slice.
5. A successful slice remains local-only, `NOT_A_RELEASE`, selector-ineligible, R2-denied and Validation-denied.

## Authority retained as denied

ACTIVE_RESEARCH_TRIAGE, LIVE_PROSPECTIVE append, selector or release mutation, R2 publication, Validation consumption, active novelty ranking, semantic or archetype promotion, C2E, C2.5, C3, OPT-C, OPT-D, probability, risk, exposure, trading, execution and agent write.

## Rollback

Stop the provider adapter, remove only an incomplete mutable workspace, and preserve any already-frozen checksum-addressed source object and incident record. No historical release or selector is changed.

## Continuation

Proceed to RPS-WP2. Continue through non-reserved gates and stop at RPS-G4 or an earlier blocker.
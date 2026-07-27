# RPS-WP2 — Blocker Packet

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP2`
- Baseline main: `d74d5a917fd7b49fec050c81232d899f00b78253`
- Branch: `build/rps-wp2-real-provider-intake`
- RPS-G1: `APPROVED`
- Status: `BLOCKED_REQUIRED_LOCAL_ARTIFACT_AND_PROVIDER_RUNTIME_UNAVAILABLE`

## Approved operation

One bounded Dukascopy GBP/USD intake for `[2026-07-24T00:00:00Z, 2026-07-27T00:00:00Z)` containing M1 BID, M1 ASK, native H1 BID and native H1 ASK, written only beneath `%OVC_EXTERNAL_ARTIFACT_ROOT%/prospective-source/intake/RPS.DUKASCOPY.GBPUSD.20260724_20260727.v1/`.

## Blocker

The connected GitHub execution surface cannot access the operator-local Windows environment, cannot resolve `%OVC_EXTERNAL_ARTIFACT_ROOT%`, and cannot invoke the operator-local Dukascopy provider adapter or receive the four source byte streams. The gate packet explicitly prohibits provider network access in CI and requires the source bytes to remain outside Git.

No provider request was attempted. No synthetic, historical, cached or repository data was substituted. No accepted source slice, source-object hash, evidence row, selector, release or remote object was created.

## Smallest lawful resolution

Run the approved local adapter from `C:\Users\Owner\OVIS\ovc-replay` with `OVC_EXTERNAL_ARTIFACT_ROOT` set to an available external-artifact root. Preserve the exact interval, four logical streams and byte limits. Then provide or commit only the compact intake receipt, source-object sizes and SHA-256 hashes, gap/reconciliation QA and frozen-slice manifest. Raw provider bytes and machine paths must remain outside Git.

## Required completion evidence

- Exact provider request receipt for all four logical streams.
- Source-object IDs, byte sizes and SHA-256 values.
- Ordering, duplicate and gap results.
- BID/ASK pairing and native-H1 reconciliation results.
- Frozen local slice manifest and checksum.
- Confirmation of `NOT_A_RELEASE`, selector-ineligible, R2-denied and Validation-denied states.

## Authority retained as denied

ACTIVE_RESEARCH_TRIAGE, LIVE_PROSPECTIVE append, selector/release/R2 mutation, Validation consumption, active novelty ranking, semantic promotion, C2E/C2.5/C3, OPT-C/OPT-D, probability, risk, exposure, trading, execution and agent write.

## Continuation point

Resume RPS-WP2 after the required local intake evidence is available. Do not proceed to RPS-G2, RPS-WP3 or RPS-WP4 before the immutable source slice is reproducible.
# RPS-G1A — July Provider Availability Incident

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Original gate: `RPS-G1`
- Original slice: `RPS.DUKASCOPY.GBPUSD.20260724_20260727.v1`
- Original interval: `[2026-07-24T00:00:00Z, 2026-07-27T00:00:00Z)`
- Incident state: `QUARANTINED_NO_ACCEPTED_SOURCE_SLICE`
- Provider request location: `OPERATOR_LOCAL_ONLY`
- Recorded on: `2026-07-27`

## Observed failure

The approved local command reached the required native-H1 BID request and received HTTP 404 for the July 2026 monthly Dukascopy BI5 object:

```text
GBPUSD/2026/06/BID_candles_hour_1.bi5
```

The path uses Dukascopy's zero-based month component; `06` is the July transport partition. The command exhausted its bounded retry policy, created no accepted source slice, and moved the incomplete staging workspace into the operator-local quarantine area.

## Evidence handling

- The quarantined local workspace is preserved outside Git.
- No machine-specific absolute path is recorded here.
- No provider transport bytes, CSV payloads, cache files or raw market data are committed.
- The quarantined attempt is not a source slice, release, selector input, R2 object, Validation input or prospective-evidence row.
- Its identity and bytes must not be reused under the replacement June slice.

## Disposition

`RPS-G1A` proposes to supersede only the unavailable intake scope with a completed-month replacement. The original July incident remains historical evidence of provider-object unavailability and is never relabelled as a June request.

## Authority retained as denied

ACTIVE_RESEARCH_TRIAGE, LIVE_PROSPECTIVE append, active novelty ranking, selector/release/R2 mutation, Validation consumption, semantic promotion, C2E/C2.5/C3, OPT-C/OPT-D, probability, risk, exposure, trading, execution and agent write remain denied.

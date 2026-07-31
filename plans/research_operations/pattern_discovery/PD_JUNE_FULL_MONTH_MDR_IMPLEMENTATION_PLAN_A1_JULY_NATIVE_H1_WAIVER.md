# PD-JUNE-FULL-MONTH-MDR Implementation Plan Amendment A1

## Court identity

- Base plan: `OVC-PD-JUNE-FULL-MONTH-MDR.v0.1`
- Amendment: `PD-JUNE-FM-A1-JULY-NATIVE-H1-WAIVER`
- Effective plan version: `0.1+A1`
- Programme: `PD-JUNE-FULL-MONTH-MDR`
- Operator decision time: `2026-07-31T15:36:00Z`
- Baseline main: `fbd8177cbff58827baeb55c9ceeb86d75d7b96f6`

## Triggering incident

The operator-local WP1 intake reached the Dukascopy July 2026 native-H1 BID object at `GBPUSD/2026/06/BID_candles_hour_1.bi5`. The provider returned HTTP 404 through every bounded retry and the attempt was quarantined as `RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1.20260731T152217Z.86351858`. No accepted source slice was created.

The operator instructed the programme to stop requiring the unavailable July import. Because the failed request was the monthly native-H1 transport, A1 waives that transport only. It does not remove July 1–2 M1 context, because doing so would recreate the June calendar-boundary insufficiency the programme was established to remove.

## Amended source rule

The target and source intervals remain unchanged:

- target: `[2026-06-01T00:00:00Z, 2026-07-01T00:00:00Z)`;
- source: `[2026-05-30T00:00:00Z, 2026-07-03T00:00:00Z)`;
- May 30–31 and July 1–2 remain context-only.

WP1 must request:

- 34 daily M1 partitions per side from May 30 through July 2 inclusive;
- native monthly H1 for May and June 2026 only, per side;
- no July 2026 native-H1 monthly object.

The provider plan therefore contains 72 objects: 68 daily M1 objects and 4 native monthly H1 objects.

## Post-target H1 construction

July 1–2 H1 context must be deterministically aggregated from complete M1 hours using the existing approved M1-to-H1 aggregation already used by source reconciliation.

Acceptance requires:

1. exactly 48 complete post-target H1 hours per side;
2. every derived hour contains exactly 60 distinct M1 members;
3. no interpolation, forward fill, repair or silent row insertion;
4. exact BID/ASK timestamp pairing on the combined H1 stream;
5. native-H1 reconciliation with zero OHLC mismatch for the May 30 through June 30 native-covered interval;
6. explicit source-object provenance `NATIVE_MAY_JUNE_PLUS_M1_DERIVED_JULY_CONTEXT`;
7. quarantine if July M1 context is absent or incomplete.

## Authority delta

`WAIVE_NATIVE_JULY_H1_IMPORT_DERIVE_POST_TARGET_H1_FROM_M1`

This is a bounded source-adapter amendment under explicit operator authority. It grants no formula, threshold, semantic, trigger, candidate, distance, cluster or model change; no promotion; no selector or release mutation; no canonical Discovery processing; no R2 publication; no Validation consumption; and no probability, risk, exposure, trading, execution or agent-write authority.

## Work and gate handling

A1 updates the source profile, intake implementation, compact evidence contracts, tests, workflows, QA, operator guide and programme state. After passing focused and complete repository tests, A1 is eligible for squash merge. WP1 then returns to the operator-local execution boundary under gate `PD-JUNE-FM-G1`.

WP2 remains blocked until the amended frozen source slice and compact receipts are returned.

## Rollback

Preserve the quarantined failed attempt and all prior programme history. Revert only A1 code, contracts, records, tests and workflows through a new non-destructive commit. Never relabel the quarantined attempt as accepted evidence or rewrite history.
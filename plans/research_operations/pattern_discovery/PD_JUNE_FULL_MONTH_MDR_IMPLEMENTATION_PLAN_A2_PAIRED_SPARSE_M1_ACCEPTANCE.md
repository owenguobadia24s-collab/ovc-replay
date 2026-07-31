# PD-JUNE-FULL-MONTH-MDR Amendment A2 — Paired Sparse M1 Acceptance

## Decision

Operator approval `PD-JUNE-FM-A2-PAIRED-SPARSE-M1-ACCEPTANCE PASS` authorises a bounded source-admissibility correction for the whole-June assessment.

The amendment accepts provider-observed absent M1 timestamps only when BID and ASK timestamp sets are exactly identical and every absence remains explicit. It does not authorise repair, interpolation, forward fill, copied closes, synthetic candles, continuity bridging or any market-model change.

## Evidence basis

The preserved quarantine diagnostic is bound by SHA-256:

`ddfc9672be23ac8a87101c2d34daa706b7f4793a6bc5c925e9c07713563fef99`

Observed evidence:

- 34,565 M1 rows per side;
- 95 identical non-weekend M1 gap runs per side;
- 138 absent M1 timestamps per side;
- zero duplicate or non-monotonic rows;
- exact M1 and H1 BID/ASK timestamp pairing;
- 483 complete M1-derived May/June H1 bars reconciled with native H1 at zero OHLC mismatch;
- 42 complete July context H1 hours per side;
- six incomplete July context hours per side.

## Unchanged boundaries

- target: `[2026-06-01T00:00:00Z, 2026-07-01T00:00:00Z)`;
- context source: `[2026-05-30T00:00:00Z, 2026-07-03T00:00:00Z)`;
- May and July: `CONTEXT_ONLY`;
- source identity: `RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1`;
- provider execution: `OPERATOR_LOCAL_ONLY`;
- CI provider execution: `DENIED`.

## Authorised implementation

1. Add an A2 intake adapter over the existing A1 implementation.
2. Retain the 72-object provider request plan.
3. Permit explicit paired M1 absence after exact BID/ASK timestamp equality is proven.
4. Preserve every gap run and absent timestamp in compact QA evidence.
5. Construct 15M, H1 and 2H outputs only from complete required M1 membership.
6. Mark incomplete dependent buckets `NOT_EVALUABLE` or `CENSORED`.
7. Prohibit candidate windows from bridging an incomplete bucket.
8. Preserve the failed A1 quarantine and diagnostic as immutable evidence.
9. Return to operator-local WP1 execution after CI and squash merge.

## Acceptance

- both approval bindings are required before execute;
- no provider execution in CI;
- no duplicate or non-monotonic rows;
- exact BID/ASK timestamp equality at M1 and combined H1;
- native May/June H1 reconciliation remains exact for complete M1 hours;
- missing timestamps and incomplete buckets are explicit;
- no repair or synthetic insertion;
- all focused and repository-wide tests pass.

## Retained prohibitions

No formula, threshold, state, trigger, candidate, distance, clustering, semantic, family, theory or model change; no selector or release mutation; no canonical Discovery append; no R2 publication; no Validation consumption; and no probability, risk, exposure, trading, execution or agent-write authority.

## Rollback

Preserve all quarantines, the diagnostic and A1 history. Revert A2 only through a new non-destructive commit. Never relabel incomplete or repaired material as accepted source evidence.

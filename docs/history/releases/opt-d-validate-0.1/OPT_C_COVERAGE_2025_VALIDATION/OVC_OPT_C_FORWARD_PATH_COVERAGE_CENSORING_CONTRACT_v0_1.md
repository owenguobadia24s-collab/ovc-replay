# OVC OPT-C Forward-Path Coverage and Censoring Contract v0.1

**Implementation ID:** `OPT-C-COVERAGE-0.1`  
**Parent contract:** `OPT-C-OUTCOME-0.1`  
**Status:** `RATIFIED IMPLEMENTATION — OUTCOMES NOT MEASURED`

## Exact path rule

For an event anchored at time `T` and horizon `H`, the required path is exactly
`4 × H` accepted 15M bars with open times:

`T, T+15m, …, T+H−15m`.

The final required bar closes at `T+H`. All required bars must come from the
sealed OPT-A canonical 15M release. No alternative clock, interpolation, flat
candle or inferred interval may repair a missing bar.

## Coverage status

- `COMPLETE`: every expected interval exists and the endpoint is inside the
  sealed source boundary.
- `CENSORED`: one or more expected intervals is absent or the endpoint extends
  beyond the sealed source boundary.

Objective censor reasons are additive:

- `ANCHOR_START_INTERVAL_MISSING`;
- `INTERNAL_INTERVALS_MISSING`;
- `ENDPOINT_INTERVAL_MISSING`;
- `SOURCE_END_TRUNCATION`.

Every record retains expected/available counts, missing-run counts, maximum run
length, first/last missing times and canonical hashes of missing times and
available bar IDs. A complete path additionally receives a canonical hash of
the exact ordered path bar IDs.

## Overlap metadata

Each anchor–horizon record counts other event anchors at the same time and
within `(T, T+H]`, across both clocks. Overlap never changes eligibility or
coverage; it prevents later analyses from assuming independent observations.

## Leakage boundary

This audit reads timestamps, bar IDs and source boundaries only. It does not
read forward OHLC values or calculate returns, excursions, path shape, frontier
outcomes, edge or execution metrics.

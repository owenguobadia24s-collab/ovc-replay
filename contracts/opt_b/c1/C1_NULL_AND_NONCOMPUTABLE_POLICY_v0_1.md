# C1 Null and Non-computable Policy v0.1

## Status

`FROZEN_AFTER_WP2`

## Principle

Missingness is evidence, not neutrality. C1 emits an arithmetic value only when the registered inputs are admissible. It never repairs, fills, substitutes or searches past a broken interval.

## Reason-code registry

| Reason code | Meaning | Record behaviour |
|---|---|---|
| `ZERO_RANGE` | Current admissible bar has `high == low` | Current-bar absolute geometry remains valid; all range-divided fields are null. |
| `NO_PRIOR_BAR` | No prior record exists at the beginning of the release/partition | Current-bar geometry valid; prior-close fields null. |
| `NO_CONTIGUOUS_PRIOR_BAR` | Expected immediately prior interval is absent, quarantined or not admissible | Current-bar geometry valid; prior-close fields null. |
| `PRIOR_IDENTITY_MISMATCH` | Prior release, manifest, instrument, clock or side differs | Current-bar geometry valid; prior-close fields null and identity issue blocks use of that prior record. |
| `PRIOR_NOT_FIRST_VALID` | Prior record was not admissible/first-valid by the current cutoff | Current-bar geometry valid; prior-close fields null. |
| `PRICE_INCREMENT_UNAVAILABLE` | Upstream price increment is absent or invalid | Price-unit fields valid where otherwise admissible; tick fields null. |
| `SOURCE_BAR_INADMISSIBLE` | Current OPT-A bar is incomplete, quarantined, control-only or otherwise not handoff eligible | No C1 record is emitted. |
| `CONTROL_CLOCK_NOT_AUTHORISED` | Clock is H1 control-only or a deferred context clock | No canonical C1 record is emitted. |
| `VALIDATION_LOCKED` | Validation identity is visible but consumption has no exact approval | No C1 record is emitted. |
| `UPSTREAM_IDENTITY_UNRESOLVED` | Exact OPT-A release, manifest, source-bar or lineage identity is missing | No C1 record is emitted. |

## Zero-range outputs

For an admissible zero-range bar:

- `range_abs = 0`
- `range_ticks = 0` when price increment is available
- `body_signed = 0`
- `body_abs = 0`
- `upper_wick_abs = 0`
- `lower_wick_abs = 0`
- `direction = FLAT`

The following are null with `ZERO_RANGE`:

- `body_utilisation`
- `upper_wick_share`
- `lower_wick_share`
- `wick_balance`
- `open_location`
- `close_location`
- `signed_efficiency`

Prior-close fields remain independently computable when a lawful contiguous prior close exists.

## Prior-close dependency

`true_range_abs`, `true_range_ticks`, `close_change` and `open_gap` may use only the immediately previous contiguous admissible close. The resolver must not:

- search backward for the nearest usable close;
- cross a gap, quarantine or partition boundary without an exact contiguous bar;
- cross release, manifest, instrument, clock or side identity;
- substitute provider-native H1 for an M1-derived canonical clock;
- substitute BID for ASK or ASK for BID.

## Gap adjacency

A current bar that is itself admissible but follows a broken interval may still receive current-bar geometry. All prior-close-dependent fields are null with `NO_CONTIGUOUS_PRIOR_BAR`. The copied source quality must preserve the upstream gap-adjacent state.

## Current source rejection

A current bar marked incomplete, quarantined, structural-control-only, optional-not-built or otherwise not handoff eligible produces no C1 record. The rejection is counted in QA/cardinality evidence; it is not represented as a neutral C1 row.

## Null representation

- Numerical null: JSON `null`.
- Every null measurement must have exactly one matching entry in `null_reasons`.
- A non-null measurement must not have a null reason.
- Unknown reason codes are prohibited.
- Empty strings, NaN, Infinity and sentinel numerics are prohibited.

## Authority boundary

This policy authorises WP3 fixture implementation only. It does not authorise market replay, release construction, publication, selector activation, Validation access or C2 consumption.
# C2 Prospective Evidence Contract v0.2 Amendment

## Decision

Replace the active v0.1 record shape for new writes with v0.2 while preserving v0.1 as historical court record.

## Field transition

- `observation_start_utc` → `market_window_start_utc`
- `observation_end_utc` → `market_window_end_utc`
- `created_at_utc` → `review_created_at_utc`
- add `trigger_first_valid_at`
- replace the undifferentiated `prospective: true` flag with `operation_mode`

Permitted operation modes are `LIVE_PROSPECTIVE`, `TIME_GATED_REPLAY` and `NON_EVIDENTIARY_REPLAY`.

## Counting rule

Only `LIVE_PROSPECTIVE` increments prospective-evidence counts or satisfies the first-real-prospective-batch boundary. Replay modes remain separately visible and cannot be promoted by relabelling.

## Migration state

At amendment time the canonical append target was absent and the accepted count remained zero. No row migration, timestamp inference, record-ID rewrite or historical relabelling was performed.

## Retained authority

Validation remains `LOCKED_UNCONSUMED`. C2E, C2.5, C3, OPT-C, OPT-D, probability, exposure, trading and execution authority remain `NONE`. Selectors, releases and R2 objects are unchanged.

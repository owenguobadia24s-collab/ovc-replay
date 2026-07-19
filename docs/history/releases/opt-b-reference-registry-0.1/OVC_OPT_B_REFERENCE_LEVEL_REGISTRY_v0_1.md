# OVC OPT-B Deterministic Reference-Level Registry v0.1

**Registry:** `OPT-B-REFERENCE-LEVELS`  
**Version:** `B-REF-0.1`  
**Status:** `BUILT FOR REPLAY VALIDATION — NOT ACTIVE`  
**OPT-A authority:** `OPT-A.GBPUSD.2026H1.v1`  
**OPT-A seal hash:** `0927f7a2b078d670370eb9ec26718f3e2ff0d97708df1f785a9333264415ef99`

## Result

| Timeframe | Source bars | Swing high | Swing low | Range high | Range low | Total levels |
|---|---:|---:|---:|---:|---:|---:|
| 15M | 11,830 | 1,366 | 1,381 | 4,341 | 4,400 | 11,488 |
| 2H | 1,521 | 189 | 180 | 545 | 575 | 1,489 |

## Frozen construction rules

### Confirmed swing 2×2

- A high must be strictly greater than the highs of two closed bars on each side.
- A low must be strictly lower than the lows of two closed bars on each side.
- Ties do not qualify.
- The level is created at the pivot close but cannot become valid until the second right-hand confirmation bar closes.
- A five-bar window may not cross a source gap.

### Rolling range 8

- Range high is the maximum high of eight contiguous closed bars.
- Range low is the minimum low of the same window.
- The levels become valid when the eighth bar closes.
- A new record is emitted only when that boundary price changes within a contiguous segment.

## Eligibility and no-lookahead boundary

A level may be supplied to a classifier only when it matches instrument, timeframe, source release and price side, and `first_valid_time <= candidate.open_time`. Multiple eligible levels remain separate records. No later bar may alter an existing level ID, price, source bars or first-valid timestamp.

## Deferred

Previous-day/week/month, initial-balance and profile levels remain excluded until their calendar and construction contracts are separately ratified. This registry does not activate the five level-dependent OPT-B terms; it supplies their deterministic inputs for the next replay stage.

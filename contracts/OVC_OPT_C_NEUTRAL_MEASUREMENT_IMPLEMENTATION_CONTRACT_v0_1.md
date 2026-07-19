# OVC OPT-C Neutral Measurement Implementation Contract v0.1

**Implementation ID:** `OPT-C-MEASURE-0.1`  
**Parent contracts:** `OPT-C-OUTCOME-0.1`, `OPT-C-COVERAGE-0.1`  
**Status:** `RATIFIED IMPLEMENTATION FOR COMPLETE 1–12H PATHS`

## Admitted records

Measurements are produced only when:

- the horizon is `1h, 2h, 4h, 8h` or `12h`;
- the coverage record is `COMPLETE`;
- the ordered path bar-ID hash replays exactly from the sealed OPT-A 15M bars.

Censored records receive no outcome row. The 24h horizon remains coverage-only
because only 36 H1 paths are complete. The 48h horizon remains blocked.

## Price and excursion measurements

All prices are bid-side decimals. One GBP/USD pip is `0.0001`.

Each outcome records:

- endpoint price and raw endpoint return;
- maximum upward and downward excursion from the anchor;
- first 15M bar-close time at each path extreme;
- whether the high or low extreme occurred first;
- endpoint close position within the forward range;
- direction-normalized endpoint, favourable and adverse movement for `UP` or
  `DOWN` anchors only.

Direction-normalized values are relative movement, never profit, loss, win or
trade performance. `MIXED` and `NONE` anchors receive no normalized values.

## Frontier and continuation measurements

Every available accepted floor and ceiling is tested independently:

- retest: the level lies within a future 15M bar range;
- loss: a future close is below a floor or above a ceiling;
- endpoint hold: the endpoint close remains on the accepted side;
- first retest/loss time: close-time resolution of the first qualifying 15M bar.

For directional anchors, continuation means a future high exceeds the event-bar
high (`UP`) or a future low breaches the event-bar low (`DOWN`). A directional
reversal through the frontier is the corresponding primary frontier loss on a
future close.

## State and overlap lineage

Each outcome binds the exact event anchor, coverage record, ordered path hash,
endpoint 15M B-STATE record, intervening B-STATE transition hash and approved
overlap metadata.

## Authority boundary

The release is descriptive OPT-C evidence. It cannot label wins/losses, select
thresholds, claim edge, recommend action, size risk or authorize execution.

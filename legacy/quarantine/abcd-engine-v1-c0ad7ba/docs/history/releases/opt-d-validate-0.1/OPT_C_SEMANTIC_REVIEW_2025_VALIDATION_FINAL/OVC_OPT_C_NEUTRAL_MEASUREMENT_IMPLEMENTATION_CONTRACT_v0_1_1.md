# OVC OPT-C Neutral Measurement Implementation Contract v0.1.1

**Implementation ID:** `OPT-C-MEASURE-0.1.1`  
**Supersedes:** `OPT-C-MEASURE-0.1`  
**Parent contracts:** `OPT-C-OUTCOME-0.1`, `OPT-C-COVERAGE-0.1`  
**Status:** `RATIFIED IMPLEMENTATION FOR COMPLETE 1–12H PATHS`

This contract preserves every v0.1 price, path, horizon, return, excursion,
continuation, endpoint-state and transition-lineage rule.

## Primary-frontier nullability clarification

A directional anchor has a primary frontier only when its anchor snapshot
contains the direction-corresponding accepted frontier and the outcome contains
that frontier test:

- `UP` requires an accepted `FLOOR`;
- `DOWN` requires an accepted `CEILING`.

If that frontier is absent, `primary_frontier_type`, primary retest, primary
loss, endpoint hold and directional reversal fields are all `null`. An
opposite-type frontier may still remain in `frontier_tests`; it cannot be
promoted into the primary role.

## Admitted records and authority

Only complete 1h, 2h, 4h, 8h and 12h paths are measured. Censored paths receive
no outcome row; 24h remains coverage-only and 48h remains blocked. All values
remain neutral descriptive evidence with no edge, recommendation, risk, trade,
production or execution authority.

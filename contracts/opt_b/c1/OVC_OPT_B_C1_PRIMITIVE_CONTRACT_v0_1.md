# OVC OPT-B.C1 Primitive Contract v0.1

## Status

`FROZEN_AFTER_WP2`

## Contract identity

- Contract ID: `OVC_OPT_B_C1_PRIMITIVE_CONTRACT_v0_1`
- Layer: `OPT-B.C1.v2`
- Formula registry: `C1.FORMULAS.v0.1`
- Record schema: `c1_bar_primitives_v0_1`
- Upstream profile: `OPT_A_V2_TO_C1_INPUT_PROFILE_v0_1`

## Authority

This contract freezes the machine-readable design for the C1 atomic-fact layer. It authorises WP3 implementation and computation on approved synthetic/golden fixtures only. It does not authorise market replay, a C1 release, R2 publication, selector activation, C2 consumption, Validation access, probability, exposure, trading or execution.

## Canonical unit

One C1 record describes one admissible closed OPT-A v2 bar for exactly one release, instrument, clock and price side.

Initial canonical clocks:

- `15M`
- `2H_A_L`

Initial sides:

- `BID`
- `ASK`

`H1_M1_DERIVED` and `H1_PROVIDER_NATIVE` are control-only and rejected by the canonical C1 input profile. `4H`, `D1`, midpoint and cross-side measures are deferred.

## Admissible inputs

C1 may read only:

1. an exact active OPT-A v2 release and manifest identity;
2. one admissible closed OPT-A bar with deterministic source-bar identity;
3. exact OHLC Decimal strings and price increment;
4. source quality, completeness, clock, side and first-valid time;
5. exact parent source-object and parent M1-bar lineage;
6. the immediately previous contiguous admissible bar only for registered prior-close formulas.

The previous bar is lawful only when it has the same OPT-A release, manifest, instrument, clock and price side; its close time equals the current open time; it is admissible; and it was first valid no later than the current bar close.

## Primitive boundary

C1 owns arithmetic observations only:

- high-low range and tick range;
- signed and absolute body;
- body utilisation;
- upper/lower wick magnitudes and shares;
- wick balance;
- open and close location in the current range;
- signed current-bar efficiency;
- arithmetic direction (`UP`, `DOWN`, `FLAT`);
- true range, close change and open gap using only the lawful immediate prior close.

## Chronology and first-valid rule

- The current bar must be closed.
- `first_valid_time` is the source bar close time.
- No future bar, later path, outcome or retrospective classification may be read.
- A prior-close primitive may not bridge a missing, quarantined, mismatched or non-contiguous interval.
- Every formula declares lookback `0` or `1`; no rolling search for a usable prior bar is permitted.

## No-threshold and no-interpretation law

The formula registry contains equations and domains, never predicates such as strong, weak, large, compressed, displacement, reclaim, rejection, acceptance, breakout, reversal, hammer or doji.

C1 must not contain:

- rolling windows, ATR, medians, volatility regimes or sequence efficiency;
- levels, containers, sessions or market-day profiles;
- state, persistence, transition or event labels;
- episodes, trajectories, families or structural meaning;
- outcomes, stories, claims, cohorts or evidence dispositions;
- midpoint, spread interpretation or cross-side repair;
- probability, eligibility, risk, trade or execution fields.

## Decimal and serialization law

- Arithmetic uses exact decimal semantics.
- Canonical stored numerical values are decimal strings, not binary floats.
- Stored values are not display-rounded.
- Ratios use exact numerator/denominator arithmetic and are null only under the registered null policy.
- Canonical serialization is UTF-8, stable key ordering and a final newline.
- Machine path, host, worker, output row and run timestamp do not enter record identity.

## Versioning

A change to any equation, unit, domain, inclusion boundary, null reason, symmetry rule, required input, chronology rule or identity component creates a new formula or contract version and requires a complete replay. Historical C1 records are never edited in place.

## QA mapping

Blocking checks:

- `C1-QA-ARITH-001` OHLC and formula arithmetic
- `C1-QA-DOMAIN-002` bounded domains and exact zero-range behaviour
- `C1-QA-CHRON-003` closed-bar and lawful-prior chronology
- `C1-QA-LEAK-004` no future/downstream dependency
- `C1-QA-LINEAGE-005` exact OPT-A identity and source lineage
- `C1-QA-DETERMINISM-006` bit-for-bit rerun
- `C1-QA-SYMMETRY-007` declared metamorphic symmetry
- `C1-QA-SERIAL-008` canonical decimal serialization and identity
- `C1-QA-CARDINALITY-009` one-or-zero record per admissible source bar
- `C1-QA-BOUNDARY-010` no C2/C/D or exposure semantics

## Rollback

Rollback removes WP3 build authority and returns C1 to `WP1_BOUNDARY_PASS_WP2_NOT_FROZEN`. It does not mutate OPT-A selectors, historical records or remote objects and cannot reactivate legacy OPT-A or OPT-B code.
# OPT-A v2 to C1 Input Profile v0.1

## Status

`FROZEN_AFTER_WP2`

## Upstream authority

C1 accepts only exact records from the active OPT-A v2 role-selector set and the `ovc-opt-a-to-opt-b-handoff/v2` envelope.

Permitted parent releases:

- `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2`
- `OPT-A.GBPUSD.DEVELOPMENT.2024.v2`
- `OPT-A.GBPUSD.VALIDATION.2025.v2` only after a separate exact Validation-consumption approval; current state remains `LOCKED_UNCONSUMED`

Prohibited parent:

- `OPT-A.GBPUSD.2026H1.v1`
- any legacy/quarantined release or unsealed workspace
- any synthetic fixture as market authority

## Required handoff fields

- handoff schema and ID;
- exact release ID, manifest ID and manifest SHA-256;
- research role and interval;
- instrument `GBPUSD`;
- source/build commit;
- active selector and authority state;
- Validation consumption state;
- surface record eligibility;
- exact source-bar ID, clock, side and first-valid time;
- OHLC Decimal strings and price increment;
- quality/admissibility state;
- parent source-object IDs and parent M1-bar IDs;
- provider, clock, aggregation, gap, volume and reconciliation contract versions.

## Canonical clocks

### 15M

- Must be an accepted OPT-A canonical 15M surface.
- Must resolve to 15 exact aligned M1 parents for the same side.
- Missing or misaligned buckets produce no C1 record.

### 2H_A_L

- Must be an accepted A-L two-hour surface.
- Must resolve to 120 exact M1 parents or eight exact accepted 15M parents under the frozen upstream contract.
- An incomplete A-L block produces no C1 record.

## Control-only and deferred clocks

- `H1_M1_DERIVED`: QA/control only; rejected by the canonical C1 profile.
- `H1_PROVIDER_NATIVE`: source corroboration only; never repairs or substitutes canonical detail.
- `4H`, `D1`: deferred and `NOT_AUTHORISED` in v0.1.

## Price-side law

Each record is exactly `BID` or `ASK`. No midpoint, spread, side merge, cross-side prior close or side substitution is permitted.

## Current-bar admissibility

A canonical C1 record requires a closed, accepted, handoff-eligible OPT-A bar. Incomplete, quarantined, optional-not-built, control-only or unresolved bars produce no record and must be counted by reason.

## Prior-bar admissibility

The optional prior bar must:

- share release ID and manifest ID;
- share instrument, clock and price side;
- have `close_time == current.open_time`;
- be accepted and first-valid by the current cutoff;
- have exact deterministic source identity and lineage.

Failure makes only prior-close-dependent fields null. C1 must not search farther backward.

## Validation lock

Validation release identity may be resolved for governance, but bar consumption remains denied while `validation_consumption_state == LOCKED_UNCONSUMED`. WP2 does not change that state.

## No-repair law

C1 must not reconstruct missing 15M bars from H1, construct canonical 2H from provider-native H1, cross a gap for a previous close, interpolate, fill, manually repair or use another side.

## Fixture authority

WP2 fixtures use synthetic handoff-shaped objects with `synthetic: true`, lifecycle `DRAFT`, authority `NONE` and selector `NONE`. They may validate contracts and WP3 code but can never become release parents, discovery seeds or market evidence.
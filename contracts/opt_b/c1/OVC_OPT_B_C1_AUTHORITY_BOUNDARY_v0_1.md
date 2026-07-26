# OPT-B.C1 v2 Authority Boundary v0.1

## Status

`FROZEN_FOR_WP2_DESIGN`

## Authority

This contract establishes the repository and dependency boundary for OPT-B.C1 v2. It authorises contract, registry, schema and synthetic-fixture work only. It does not authorise market replay, a C1 release, R2 publication, selector activation, C2 consumption, probability, exposure, trading or execution.

## Upstream source authority

C1 may consume only the active OPT-A v2 role-selector set and the exact sealed handoff objects bound to:

- `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2`
- `OPT-A.GBPUSD.DEVELOPMENT.2024.v2`
- `OPT-A.GBPUSD.VALIDATION.2025.v2`, identity-visible but `LOCKED_UNCONSUMED`

Every future C1 record must resolve to an exact OPT-A release ID, manifest ID, source observation ID, clock, price side, quality state and contract version.

Historical OPT-A v1, the quarantined legacy engine and historical OPT-B outputs are prohibited as active parents, formula authority, selector fallback, parameter source or discovery seed.

## C1 epistemic responsibility

C1 owns atomic, stateless, bar-local facts and the minimum lawful contiguous-prior-close dependency needed for explicitly registered primitives.

Permitted categories:

- current-bar OHLC geometry;
- range, body and wick measurements;
- signed current-bar change where defined;
- exact price-side and clock identity;
- source quality and missingness propagation;
- deterministic record identity and formula-version lineage.

C1 does not own:

- rolling windows, ATR or volatility regimes;
- reference levels, containers or sessions;
- temporal state, persistence or transitions;
- C2.5 events or semantic candle names;
- episodes, trajectories or C3 meaning;
- future paths, outcomes, cohorts, claims or trade labels;
- cross-side midpoint, spread interpretation or inferred repair.

## Canonical initial scope

- Instrument: `GBPUSD`
- Canonical candidate clocks: `15M`, `2H_A_L`
- Price sides: `BID`, `ASK`, preserved independently
- Control-only clocks: `H1_M1_DERIVED`, `H1_PROVIDER_NATIVE`
- Validation: identity registered, data access denied until a separate exact approval

No missing source bar may be repaired through another clock, another side, native H1, interpolation or manual substitution.

## Dependency allowlist

C1 may read:

1. active OPT-A v2 selector and release registries;
2. the v0.2 OPT-A-to-OPT-B handoff schema and contract;
3. exact sealed OPT-A observation records approved for the role being replayed;
4. C1-owned contracts, schemas, formula registries and parameter-free configuration;
5. cross-cutting QA definitions and C1-specific assertions.

## Dependency denylist

C1 must not read:

- `legacy/quarantine/**` at runtime;
- historical OPT-A v1 payloads or seals as market parents;
- OPT-B.C2, C2E, C2.5 or C3 outputs;
- OPT-C or OPT-D outputs;
- future timestamps, realised paths or outcomes;
- active thresholds, market narratives, story/candidate records or execution objects.

## Storage boundary

Git stores compact contracts, schemas, registries, fixtures, tests, manifests, QA packets and decisions. Full C1 streams, raw bars, caches and large evidence remain outside Git and checksum-addressed.

## Authority progression

`WP1 boundary -> WP2 contracts/schemas -> WP3 synthetic engine trust -> WP4 candidate replay/local release -> WP5 publication/shadow activation`

Each later transition requires its own exact operator decision. WP1 changes no market selector.

## Rollback

WP1 rollback removes the C1 build approval and returns C1 to `DESIGN_AND_FIXTURES_ONLY`. It does not alter the active OPT-A selector set and can never reactivate historical v1 or the legacy engine.

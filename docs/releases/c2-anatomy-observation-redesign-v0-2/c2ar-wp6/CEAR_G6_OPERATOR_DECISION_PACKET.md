# CEAR-G6 — Integrated Shadow Freeze and Formula-Profile Decision

**Programme:** `OVC-C2-ANATOMY-REDESIGN-v0.2`  
**Plan:** `OVC-C2-ANATOMY-REDESIGN-IMPLEMENTATION / 0.2-REVISED`  
**Gate class:** `OPERATOR_REQUIRED`  
**Recommended decision:** `PASS`  
**Exact approval command:** `OVC APPROVE CEAR-G6 PASS`

## Decision requested

Approve the already-tested observation, horizon, level, container and relation shadow revisions as one hash-pinned `SHADOW_FROZEN` interface set, and authorise bounded implementation of five inactive, noncanonical formula profiles:

- `C2.FORMULA.LOCATION.RAW_GEOMETRY.v1`
- `C2.FORMULA.MOTION.TYPED_HORIZON_DELTA.v1`
- `C2.FORMULA.ORGANISATION.CONTAINER_GRAPH.v1`
- `C2.FORMULA.INTERACTION.RAW_TRANSITION_INPUT.v1`
- `C2.FORMULA.QUALITY.PER_COMPONENT_COMPUTABILITY.v1`

This decision does **not** activate a formula, selector, parameter, scale, threshold, detector, release or semantic label.

## Evidence completed

| Packet | Gate | Result | Merge |
|---|---|---|---|
| C2AR-WP0 | C2AR-G0A | PASS | `2ebb1b5ab572fd8edad5e7096240ebeb9dae0e6b` |
| C2AR-WP1 | CEAR-G1 | PASS | `288fe6b96449d4af630ac764a8c1a1f40bfe9cab` |
| C2AR-WP2 | CEAR-G2 | PASS | `95615ec66ef7c69082d55e1cf1d8cf7817d2a814` |
| C2AR-WP3 | CEAR-G3 | PASS | `d28638dbc1497d229e8b7e9a28b385cce75331b9` |
| C2AR-WP4 | CEAR-G4 | PASS | `8375b495f01bf91cb2ac5c3ab31730c1c40dd491` |
| C2AR-WP5 | CEAR-G5 | PASS | `a2ab0f134c856e6dc8106b694604226839df565f` |
| C2AR-WP5.5 | C2AR-G5.5 | PASS | `b7a77daec5062c8bbd9c1fa32f41fd1c2c77c26d` |

The canonical synthetic smoke proved the complete `observation → horizon → level → container → relation` topology with deterministic stage hashes, no future-member breach, visible ambiguity/censorship/exclusions and zero active authority.

## Current authority

The active C2 discovery selector remains `SELECTOR.OPT-B.C2.GBPUSD.v2`, targeting `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2`. Validation remains `LOCKED_UNCONSUMED`. No active C2 object is changed by this packet.

## Proposed delta

`PASS` authorises only:

1. freezing the five named shadow revisions as an immutable integrated interface set;
2. requiring new versions and supersession records for future changes;
3. materialising contracts, schemas, fixtures, deterministic implementations and tests for the five formula profiles;
4. running inactive read-only shadow computation over synthetic or separately authorised sealed sources.

It does not authorise selector activation or replacement, numeric thresholds, parameter selection, semantic promotion, detector policy, parent resolver policy, denominator policy, rule promotion, new provider intake, canonical/R2 publication, Validation consumption, C2E/C2.5/C3, probability, risk, exposure, trading, execution or agent writes.

## QA and warnings

The prerequisite programme tests and merge-readiness checks passed. The gate branch must pass its own exact-head tests before it is presented as final.

Non-blocking warnings:

- no real-market population replay has selected numeric formula thresholds or profile variants;
- the exact original P2-D11 label and CEAR-ER1 packet bytes were unavailable in the runtime, so no external claim was reconstructed;
- CEAR-G7 through CEAR-G10 remain separate operator-required gates.

## Rollback

Before approval, close or supersede this proposal; it has no authority effect. After approval, any change requires a new versioned supersession packet and operator decision. Existing frozen hashes, evidence and decisions remain immutable. Active C2 remains unchanged.

## Exact work after PASS

Record the operator decision, materialise the integrated freeze manifest and digest, transition the five revisions to `SHADOW_FROZEN`, implement the five inactive formula profiles, run targeted and complete tests plus authorised shadow comparisons, merge eligible non-reserved packets, then continue to WP7 and stop at CEAR-G7 before transition/detector-policy authority.

The machine-readable court record is `CEAR_G6_OPERATOR_DECISION_PACKET.json`.

# Current status

Snapshot date: 25 July 2026.

## Integrated baseline

The reset and the first three OPT-A v2 work packets are merged into `main`:

- R0 reset: `a9902c97e21131b1882b4c11ca3a2a79273e7c77`
- WP1 release governance: `5c567c1ba7de57d83079200c006f991d41642310`
- WP2 evidence-store lifecycle: `91d57980be84239de69de00c43649d20a2acd7fe`
- WP3 provider, clock, release-split and handoff contracts: `087cfe47c2dceffc89d43f2795ebd28dd35d3d3d`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and non-reproducible from its exact sealed bytes. It cannot be reused, published, selected or used as rollback authority.

## A2-G0 foundation review

A2-G0 is sealed as `PASS`. The combined foundation now includes:

- exact discovery, development and validation release identities;
- all role selectors at `NONE`;
- 2025 validation at `LOCKED_UNCONSUMED` with default access denied;
- process-only external-root, deterministic inventory, gated freeze, exact publication approval and read-only readiness controls;
- frozen Dukascopy GBPUSD M1/H1 BID/ASK source-object contracts;
- UTC half-open A–L clock and exact aggregation, gap, volume and reconciliation rules;
- a sealed one-way OPT-A-to-OPT-B.C1 handoff contract with no active handoff;
- synthetic, non-authoritative contract fixtures and repository guard tests;
- integrated canonical CI with 100 tests passing and no failures or errors before gate sealing.

A2-G0 performs no provider request and introduces no market authority.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / WP2_MERGED_PASS` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 | `FOUNDATION_PASS_INTAKE_NOT_RELEASE` | `NONE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

## External evaluation boundary

Credential-free GitHub CI cannot inspect the operator's Windows artifact root, provider connectivity, environment-only rclone configuration, the current R2 object inventory or the live bucket-lock state. These remain `NOT_EVALUATED_BY_GITHUB_RUNNER` and must be checked in the operator-local preflight before the relevant intake or publication action.

## Authority granted after merge

A passing merged A2-G0 authorises the bounded `WP4 — provider intake implementation and execution` packet. The first provider network request remains denied until the operator-local preflight confirms the external root, path safety, workspace uniqueness, local capacity and repository secret boundary.

## Authority still withheld

Canonical R2 publication, treating mutable workspace bytes as a release, selector activation, validation design/threshold consumption, active OPT-A-to-OPT-B handoff, OPT-B/C/D market claims, probability, exposure, trading and execution remain unauthorised.

## Next packet

`WP4 — provider intake implementation and bounded execution`, after A2-G0 PR review and merge.
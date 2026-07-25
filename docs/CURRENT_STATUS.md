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

A2-G0 reviews the combined WP1–WP3 foundation. The repository currently has:

- exact discovery, development and validation release identities;
- all role selectors at `NONE`;
- 2025 validation at `LOCKED_UNCONSUMED` with default access denied;
- process-only external-root, deterministic inventory, gated freeze, exact publication approval and read-only readiness controls;
- frozen Dukascopy GBPUSD M1/H1 BID/ASK source-object contracts;
- UTC half-open A–L clock and exact aggregation, gap, volume and reconciliation rules;
- a sealed one-way OPT-A-to-OPT-B.C1 handoff contract with no active handoff;
- synthetic, non-authoritative contract fixtures and repository guard tests.

The foundation review result is `PENDING_CI`. No provider request is performed by the review.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / WP2_MERGED_PASS` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 | `A2_G0_PENDING_CI / DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

## External evaluation boundary

Credential-free GitHub CI cannot inspect the operator's Windows artifact root, provider connectivity, environment-only rclone configuration, the current R2 object inventory or the live bucket-lock state. These remain `NOT_EVALUATED_BY_GITHUB_RUNNER` and must be checked in the operator-local preflight before the relevant intake or publication action.

## Authority still withheld

Until A2-G0 is sealed and merged, provider intake remains blocked. Canonical R2 publication, selector activation, validation design/threshold consumption, active OPT-A-to-OPT-B handoff, OPT-B/C/D market claims, probability, exposure, trading and execution remain unauthorised regardless of the A2-G0 result.

## Next decision

Complete canonical CI and operator review of A2-G0. A passing merged gate authorises the bounded WP4 provider-intake packet, subject to the mandatory operator-local preflight recorded in the gate packet.
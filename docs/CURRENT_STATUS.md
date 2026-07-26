# Current status

Snapshot date: 26 July 2026.

## Integrated baseline

The reset and OPT-A v2 build line through selector activation are merged or represented by the current A2-G5 activation branch:

- R0 reset: `a9902c97e21131b1882b4c11ca3a2a79273e7c77`
- WP1 release governance: `5c567c1ba7de57d83079200c006f991d41642310`
- WP2 evidence-store lifecycle: `91d57980be84239de69de00c43649d20a2acd7fe`
- WP3 provider, clock, release-split and handoff contracts: `087cfe47c2dceffc89d43f2795ebd28dd35d3d3d`
- A2-G0 foundation review: `f4286bdb9d816ba12c77a4bb09604f462a6dc87e`
- WP4 provider population intake: `b4358c0f14186b55af43eda0c77299791fe4e774`
- A2-G1 population intake integrity: `6599919f7cd2d4e4d93e2d76c2bcf4eb4f70314d`
- WP5 role workspace construction: `bce2499dff255076b2fe297035d8923f4a21776c`
- A2-G2 observation review: `a7a99c7679a06fda3173592abeafe56a429c2e9f`
- A2-G3 role release freeze execution: `8c4c6c70da6f3f8b400d06df990500702813ff39`
- WP6 canonical R2 publication: `8f0dd49e489b531df8998b4fc1575d6fb11317d1`
- A2-G4 remote publication review: `a58960fcf47ed9dfc63feffa860b44e2101ffbcd`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and prohibited as a selector or rollback target.

## A2-G5 selector-set activation

A2-G5 activated the exact three A2-G4 remotely verified releases as one atomic selector set: `SELECTOR.OPT-A.GBPUSD.ROLESET.v1`.

| Role | Release | Authority | Selector | Consumption |
|---|---|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `ACTIVE_DISCOVERY` | `ACTIVE` | `NOT_APPLICABLE` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `ACTIVE_DEVELOPMENT` | `ACTIVE` | `NOT_APPLICABLE` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `ACTIVE_VALIDATION` | `ACTIVE` | `LOCKED_UNCONSUMED` |

The activation binds the exact r2 manifest IDs and SHA-256 values recorded by A2-G4. No release bytes or remote objects were mutated.

## Quarantine disposition

The **21,410** side-specific derived-bucket quarantine records remain bound to:

`RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS`

They remain excluded from accepted observations, fills, interpolation, substitution, manual repair and downstream parentage.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / REMOTE_VERIFIED` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 role set | `A2_G5_PASS / ACTIVE` | `ACTIVE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

Validation remains `LOCKED_UNCONSUMED`, default deny and unavailable to model design, threshold selection, semantic review or case selection.

## Authority boundaries

A2-G5 grants active sealed-observation input authority only. It does not activate an OPT-A-to-OPT-B handoff, OPT-B/C/D classifiers or claims, probability, exposure, trading or execution.

Rollback is an atomic transition of all three OPT-A role selectors to `NONE`. It does not reactivate historical v1 or alter any immutable R2 object.

## Next boundary

OPT-A v2 is complete as the active observation foundation. The next bounded programme may begin with OPT-B.C1 v2 under its own contracts, release gates and operator approvals.

# Current status

Snapshot date: 25 July 2026.

## Integrated baseline

The reset, foundation work and A2-G0 review are merged into `main`:

- R0 reset: `a9902c97e21131b1882b4c11ca3a2a79273e7c77`
- WP1 release governance: `5c567c1ba7de57d83079200c006f991d41642310`
- WP2 evidence-store lifecycle: `91d57980be84239de69de00c43649d20a2acd7fe`
- WP3 provider, clock, release-split and handoff contracts: `087cfe47c2dceffc89d43f2795ebd28dd35d3d3d`
- A2-G0 foundation review: `f4286bdb9d816ba12c77a4bb09604f462a6dc87e`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and non-reproducible from its exact sealed bytes. It cannot be reused, published, selected or used as rollback authority.

## WP4 actual GBP/USD provider population intake

WP4 is in `PENDING_EXECUTION` state. The workflow is configured to acquire the exact Dukascopy GBP/USD population for `[2021-01-01T00:00:00Z, 2026-01-01T00:00:00Z)`:

- 60 monthly partitions;
- M1 BID and ASK;
- H1 BID and ASK;
- 240 planned source objects;
- 144 discovery objects for 2021–2023;
- 48 development objects for 2024;
- 48 validation objects for 2025.

The workflow uses an external runner workspace outside Git, retains the pinned provider-adapter transport cache, validates every accepted CSV and uploads temporary yearly evidence artifacts. Raw market bytes do not enter the repository.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / WP2_MERGED_PASS` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 | `WP4_PENDING_EXECUTION / INTAKE_NOT_RELEASE` | `NONE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

Validation remains `LOCKED_UNCONSUMED`, default deny and unavailable to design or threshold selection.

## Storage boundary

Actual market payloads are stored only in GitHub Actions evidence artifacts during WP4:

- yearly source-data bundles: 30-day retention;
- compact monthly and aggregate summaries: 90-day retention;
- canonical R2 mutation: none;
- Git market payloads: denied.

These artifacts are temporary intake evidence, not canonical role releases.

## Authority still withheld

Release freezing, canonical R2 publication, selector activation, validation design/threshold consumption, active OPT-A-to-OPT-B handoff, OPT-B/C/D market claims, probability, exposure, trading and execution remain unauthorised.

## Completion condition

WP4 passes only after the provider pilot, all five yearly jobs, the exact 60-month/240-object aggregate and final canonical CI pass. Until then, the branch remains unmerged and no release authority exists.
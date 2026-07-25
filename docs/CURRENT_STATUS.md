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

WP4 is sealed as `PASS` and awaits operator review and merge.

The successful Dukascopy intake covers `[2021-01-01T00:00:00Z, 2026-01-01T00:00:00Z)` and contains:

- **60** accepted UTC calendar-month partitions;
- independent M1 BID, M1 ASK, H1 BID and H1 ASK objects;
- **240** accepted source objects;
- **3,781,810** accepted rows across the four object families;
- **216,656,289** accepted CSV bytes;
- aggregate QA state `PASS`;
- no release, selector, handoff or market authority.

Role allocation remains:

- 144 discovery objects for 2021–2023;
- 48 development objects for 2024;
- 48 validation objects for 2025.

Validation remains `LOCKED_UNCONSUMED`, default deny and unavailable to design or threshold selection.

## Execution evidence

Workflow run `30175183492` completed successfully:

- repository unit tests: PASS;
- January 2021 provider pilot: PASS;
- yearly population jobs for 2021, 2022, 2023, 2024 and 2025: PASS;
- exact 60-month / 240-object aggregate: PASS.

Final pre-seal canonical CI run `30176467243` passed **107 tests** with zero failures and zero errors.

The executed adapter was `OVC_DIRECT_BI5_CANDLE_ADAPTER` version `1.0.1`. Exact provider BI5 transport objects, generated CSV objects, intake records and source identities are held in temporary GitHub Actions evidence artifacts. The five yearly compressed artifacts total **85,076,759 bytes**.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / WP2_MERGED_PASS` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 | `WP4_PASS / INTAKE_COMPLETE_NOT_RELEASE` | `NONE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

## Storage boundary

- Raw provider and market payloads in Git: denied.
- Yearly provider evidence bundles: temporary GitHub Actions artifacts with 30-day retention.
- Compact summaries and aggregate execution records: 90-day Actions retention plus compact Git records.
- Canonical Cloudflare R2 mutation: none.

These artifacts are intake evidence, not canonical role releases. Their exact IDs, digests, sizes and expiry times are recorded in `docs/releases/opt-a-v2/intake/WP4_ACTIONS_ARTIFACT_INVENTORY.json`.

## Authority still withheld

Release freezing, canonical R2 publication, selector activation, validation design/threshold consumption, active OPT-A-to-OPT-B handoff, OPT-B/C/D market claims, probability, exposure, trading and execution remain unauthorised.

## Next packet

After merge, the next bounded packet is `WP5 — role workspace construction and QA`. It may transform the accepted intake evidence into governed discovery, development and locked-validation workspaces, but release freezing and publication remain separate gates.
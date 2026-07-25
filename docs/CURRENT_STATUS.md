# Current status

Snapshot date: 25 July 2026.

## Integrated baseline

The reset, foundation work, A2-G0 review and WP4 provider intake are merged into `main`:

- R0 reset: `a9902c97e21131b1882b4c11ca3a2a79273e7c77`
- WP1 release governance: `5c567c1ba7de57d83079200c006f991d41642310`
- WP2 evidence-store lifecycle: `91d57980be84239de69de00c43649d20a2acd7fe`
- WP3 provider, clock, release-split and handoff contracts: `087cfe47c2dceffc89d43f2795ebd28dd35d3d3d`
- A2-G0 foundation review: `f4286bdb9d816ba12c77a4bb09604f462a6dc87e`
- WP4 provider population intake: `b4358c0f14186b55af43eda0c77299791fe4e774`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and non-reproducible from its exact sealed bytes. It cannot be reused, published, selected or used as rollback authority.

## A2-G1 population intake integrity

A2-G1 is sealed as `PASS` on the build branch.

The five WP4 yearly evidence artifacts were independently downloaded and fully audited:

- **60/60** UTC calendar-month partitions;
- **240/240** M1/H1 BID/ASK source objects;
- **3,781,810** accepted rows;
- **216,656,289** accepted CSV bytes;
- **3,772** retained Dukascopy BI5 transport chunks;
- **0** byte-identity, request-lineage, schema, timestamp, duplicate, gap-accounting or quarantine violations.

Every accepted object has matching SHA-256 and byte counts across its CSV, downloader receipt, intake record and source identity. Every retained transport chunk has matching byte identity and explicit provider request lineage.

A2-G1 therefore authorises the provider objects to enter governed mutable discovery, development and locked-validation workspaces. It does not make them frozen releases or accepted OPT-A observations.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / WP2_MERGED_PASS` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 intake | `A2_G1_PASS / WORKSPACE_ENTRY_AUTHORISED` | `NONE` |
| OPT-A v2 observations | `NOT_CONSTRUCTED / A2_G2_REQUIRED` | `NONE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

Validation remains `LOCKED_UNCONSUMED`, default deny and unavailable to design or threshold selection.

## Storage boundary

- Raw provider and market payloads in Git: denied.
- Yearly provider evidence bundles: temporary GitHub Actions artifacts with 30-day retention.
- Canonical Cloudflare R2 mutation: none.
- Release freezing: none.

## Authority still withheld

Observation acceptance, release freezing, canonical R2 publication, selector activation, validation consumption, active OPT-A-to-OPT-B handoff, OPT-B/C/D market claims, probability, exposure, trading and execution remain unauthorised.

## Next gate

`A2-G2 — Observation construction`, executed through the bounded `WP5 — role workspace construction and QA` packet.

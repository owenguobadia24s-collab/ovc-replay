# Current status

Snapshot date: 25 July 2026.

## Integrated baseline

The reset, OPT-A v2 foundation, provider population, population-integrity review, WP5 workspace construction and A2-G2 observation review are merged into `main`:

- R0 reset: `a9902c97e21131b1882b4c11ca3a2a79273e7c77`
- WP1 release governance: `5c567c1ba7de57d83079200c006f991d41642310`
- WP2 evidence-store lifecycle: `91d57980be84239de69de00c43649d20a2acd7fe`
- WP3 provider, clock, release-split and handoff contracts: `087cfe47c2dceffc89d43f2795ebd28dd35d3d3d`
- A2-G0 foundation review: `f4286bdb9d816ba12c77a4bb09604f462a6dc87e`
- WP4 provider population intake: `b4358c0f14186b55af43eda0c77299791fe4e774`
- A2-G1 population intake integrity: `6599919f7cd2d4e4d93e2d76c2bcf4eb4f70314d`
- WP5 role workspace construction: `bce2499dff255076b2fe297035d8923f4a21776c`
- A2-G2 observation review: `a7a99c7679a06fda3173592abeafe56a429c2e9f`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and non-reproducible from its exact sealed bytes. It cannot be reused, published, selected or used as rollback authority.

## A2-G3 role release freeze

A2-G3 executed successfully on commit `8c4c6c70da6f3f8b400d06df990500702813ff39`. Canonical tests (`30179286518`) and the governed freeze workflow (`30179286521`) passed.

Three candidate role releases were frozen from the exact A2-G2 reviewed workspace identities:

| Role | Release | Files | Bytes | Artifact |
|---|---|---:|---:|---:|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | 292 | 155,631,400 | `8625089938` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | 100 | 52,761,781 | `8625090401` |
| Validation — locked | `OPT-A.GBPUSD.VALIDATION.2025.v2` | 100 | 52,303,593 | `8625090861` |

Each release contains accepted canonical observations, the exact reviewed workspace manifest, a separately packaged quarantine ledger, a deterministic release descriptor, a release inventory and a freeze receipt. Existing release roots cannot be overwritten.

The frozen releases are `CANDIDATE / RELEASE_FROZEN / LOCAL_ARTIFACT_ONLY`. They are not published, selected or active.

## Quarantine disposition

The **21,410** side-specific derived-bucket quarantine records remain bound to:

`RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS`

They are preserved in each release's QA ledger and remain excluded from accepted observations, interpolation, fill, substitution, manual repair, selector input and OPT-B parentage.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / WP2_MERGED_PASS` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 intake | `A2_G1_PASS` | `NONE` |
| OPT-A v2 observations | `A2_G2_PASS / REVIEWED` | `NONE` |
| OPT-A v2 role releases | `A2_G3_PASS / RELEASE_FROZEN / LOCAL_ARTIFACT_ONLY` | `NONE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

Validation remains `LOCKED_UNCONSUMED`, default deny and unavailable to design, threshold selection or case selection.

## Storage boundary

- Raw provider and market payloads in Git: denied.
- Frozen role releases: temporary GitHub Actions artifacts expiring 24 August 2026.
- Compact A2-G3 report: artifact `8625090992`, retained until 23 October 2026, plus a Git execution receipt.
- Canonical Cloudflare R2 mutation: none.
- Active selector mutation: none.

## Authority still withheld

Canonical R2 publication, selector activation, validation consumption, active OPT-A-to-OPT-B handoff, OPT-B/C/D market claims, probability, exposure, trading and execution remain unauthorised.

## Next boundary

A separate publication-approval and remote-verification packet is required before any R2 mutation. Publication and selector activation remain independent operator decisions.

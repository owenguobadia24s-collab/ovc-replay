# Current status

Snapshot date: 26 July 2026.

## Integrated baseline

The reset and OPT-A v2 build line through canonical publication are merged into `main`:

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

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and non-reproducible from its exact sealed bytes. It cannot be reused, published, selected or used as rollback authority.

## A2-G4 remote publication review

A2-G4 independently reviewed WP6 workflow run `30181995980` and publication-report artifact `8625889699`.

The review confirmed:

- the artifact ZIP matched digest `sha256:67f9ea95026c60a6c42446974a887f9a900a2fd0809ee09a685d7ed65b827d3f`;
- the compact publication report self-hash recomputed exactly;
- every remote manifest matched its deterministic local manifest;
- every local-versus-remote manifest diff was empty;
- the complete remote payload for all three releases passed byte-count and SHA-256 readback;
- selectors were not mutated and Validation remained locked.

A2-G4 decision: `PASS`.

## Remotely verified releases

| Role | Release | Manifest | Files | Bytes | Authority |
|---|---|---|---:|---:|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2` | 293 | 155,632,392 | `SHADOW / NONE selected` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r2` | 101 | 52,762,768 | `SHADOW / NONE selected` |
| Validation — locked | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `MANIFEST.OPT-A.GBPUSD.VALIDATION.2025.v2.r2` | 101 | 52,304,577 | `SHADOW / LOCKED_UNCONSUMED` |

All three releases are now `REMOTE_VERIFIED / PUBLISHED / SHADOW_NOT_SELECTED`.

## Quarantine disposition

The **21,410** side-specific derived-bucket quarantine records remain bound to:

`RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS`

They remain preserved in QA lineage and excluded from accepted observations, interpolation, fills, substitution, manual repair and any active selector input.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / WP6_REMOTE_VERIFIED` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 intake | `A2_G1_PASS` | `NONE` |
| OPT-A v2 observations | `A2_G2_PASS / REVIEWED` | `NONE` |
| OPT-A v2 role releases | `A2_G4_PASS / REMOTE_VERIFIED / SHADOW_NOT_SELECTED` | `NONE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

Validation remains `LOCKED_UNCONSUMED`, default deny and unavailable to design, threshold selection, semantic review or case selection.

## Storage boundary

- Raw provider and market payloads in Git: denied.
- Canonical role releases: immutable in Cloudflare R2 under exact r2 manifest namespaces.
- Compact WP6 publication report and A2-G4 review: stored in Git.
- Active selector mutation: none.

## Authority still withheld

Selector activation, Validation consumption, an active OPT-A-to-OPT-B handoff, OPT-B/C/D market claims, probability, exposure, trading and execution remain unauthorised.

## Next boundary

`A2-G5 — selector-set activation`

A2-G5 requires exact remote-manifest binding, an atomic role-selector proposal, preserved Validation lock, rollback-to-`NONE` verification and a separate operator activation decision.

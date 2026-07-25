# Current status

Snapshot date: 25 July 2026.

## Integrated baseline

The reset, OPT-A v2 foundation, provider population, population-integrity review and WP5 workspace construction are merged into `main`:

- R0 reset: `a9902c97e21131b1882b4c11ca3a2a79273e7c77`
- WP1 release governance: `5c567c1ba7de57d83079200c006f991d41642310`
- WP2 evidence-store lifecycle: `91d57980be84239de69de00c43649d20a2acd7fe`
- WP3 provider, clock, release-split and handoff contracts: `087cfe47c2dceffc89d43f2795ebd28dd35d3d3d`
- A2-G0 foundation review: `f4286bdb9d816ba12c77a4bb09604f462a6dc87e`
- WP4 provider population intake: `b4358c0f14186b55af43eda0c77299791fe4e774`
- A2-G1 population intake integrity: `6599919f7cd2d4e4d93e2d76c2bcf4eb4f70314d`
- WP5 role workspace construction: `bce2499dff255076b2fe297035d8923f4a21776c`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and non-reproducible from its exact sealed bytes. It cannot be reused, published, selected or used as rollback authority.

## A2-G2 observation-construction review

A2-G2 is `PASS` after the role workspaces were rebuilt with portable manifest paths and exact missing-timestamp evidence. Both the canonical test workflow (`30178480639`) and role-workspace workflow (`30178480623`) passed from review execution commit `8d62471c3a9d81e46d5193e82d3b64497e5b3853`.

The reviewed mutable workspaces contain:

- discovery: **144** source objects and **288** observation objects for 2021–2023;
- development: **48** source objects and **96** observation objects for 2024;
- locked validation: **48** source objects and **96** observation objects for 2025;
- observation clocks: M1, 15M, H1_M1_DERIVED and 2H_A_L;
- separate BID and ASK observation chains;
- exact byte identities for all **480** observation objects.

Independent review verified the Actions artifact digests, canonical manifest self-hashes, observation hashes and sizes, portable paths, exact quarantine timestamp sets, unique bucket identities, coverage arithmetic and validation default deny. Review violations after remediation: **0**.

## Quarantine disposition

The workspaces retain **21,410 side-specific derived-bucket quarantine records**, representing **10,705 clock-time bucket locations** recorded consistently on both BID and ASK:

- discovery: **12,104**;
- development: **4,862**;
- validation: **4,444**.

All have reason `INCOMPLETE_OR_NONCONTIGUOUS_M1_BUCKET`.

Their disposition is `RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS`. They remain traceable evidence of source-chain incompleteness and are prohibited from accepted observations, interpolation, fill, provider-native H1 substitution, cross-side substitution, manual repair, selector input and OPT-B parentage.

A2-G3 may freeze accepted exact observations and package the quarantine ledger alongside them. It may not promote quarantined buckets into market truth.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / WP2_MERGED_PASS` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 intake | `A2_G1_PASS / WORKSPACE_ENTRY_AUTHORISED` | `NONE` |
| OPT-A v2 observations | `A2_G2_PASS / REVIEWED_MUTABLE_ROLE_WORKSPACES` | `NONE` |
| OPT-A v2 role freeze | `A2_G3_BOUNDED_PACKET_AUTHORISED` | `NONE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

Validation remains `LOCKED_UNCONSUMED`, default deny and unavailable to design, threshold selection or case selection.

## Storage boundary

- Raw provider and market payloads in Git: denied.
- Reviewed role workspaces: temporary GitHub Actions artifacts expiring 24 August 2026.
- Compact review and execution records: retained in Git; compact Actions report retained for 90 days.
- Canonical Cloudflare R2 mutation: none.
- Frozen role releases: none.

## Authority still withheld

Canonical R2 publication, selector activation, validation consumption, active OPT-A-to-OPT-B handoff, OPT-B/C/D market claims, probability, exposure, trading and execution remain unauthorised.

## Next gate

`A2-G3 — role release freeze`, bounded to the reviewed artifact identities and quarantine disposition recorded in `docs/releases/opt-a-v2/observations/A2_G2_OPERATOR_REVIEW.md`.

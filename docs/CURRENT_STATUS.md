# Current status

Snapshot date: 25 July 2026.

## Integrated baseline

The reset, foundation work, A2-G0 review, WP4 provider intake and A2-G1 population-integrity review are merged into `main`:

- R0 reset: `a9902c97e21131b1882b4c11ca3a2a79273e7c77`
- WP1 release governance: `5c567c1ba7de57d83079200c006f991d41642310`
- WP2 evidence-store lifecycle: `91d57980be84239de69de00c43649d20a2acd7fe`
- WP3 provider, clock, release-split and handoff contracts: `087cfe47c2dceffc89d43f2795ebd28dd35d3d3d`
- A2-G0 foundation review: `f4286bdb9d816ba12c77a4bb09604f462a6dc87e`
- WP4 provider population intake: `b4358c0f14186b55af43eda0c77299791fe4e774`
- A2-G1 population intake integrity: `6599919f7cd2d4e4d93e2d76c2bcf4eb4f70314d`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and non-reproducible from its exact sealed bytes. It cannot be reused, published, selected or used as rollback authority.

## WP5 / A2-G2 role workspace construction

WP5 executed successfully on workflow run `30177706792` from branch commit `6dd4e092caa6d8dbaaff0b9b41f8821e454120cd`.

The verified WP4 population was separated into governed mutable role workspaces:

- discovery: **144** source objects and **288** observation objects for 2021–2023;
- development: **48** source objects and **96** observation objects for 2024;
- locked validation: **48** source objects and **96** observation objects for 2025;
- observation clocks: M1, 15M, H1_M1_DERIVED and 2H_A_L;
- price sides: BID and ASK remain separate;
- incomplete or non-contiguous derived buckets are quarantined rather than filled or interpolated.

Recorded incomplete-bucket quarantines are 12,104 discovery, 4,862 development and 4,444 validation. These warnings remain explicit in each workspace manifest and must be reviewed before A2-G3 release freeze.

Both the canonical repository test workflow (`30177706768`) and the WP5 construction workflow passed. The mutable workspaces are retained as temporary Actions evidence artifacts; no market payload entered Git.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / WP2_MERGED_PASS` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 intake | `A2_G1_PASS / WORKSPACE_ENTRY_AUTHORISED` | `NONE` |
| OPT-A v2 observations | `WP5_PASS / MUTABLE_ROLE_WORKSPACES / A2_G2_REVIEW_REQUIRED` | `NONE` |
| OPT-B.C1 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

Validation remains `LOCKED_UNCONSUMED`, default deny and unavailable to design or threshold selection.

## Storage boundary

- Raw provider and market payloads in Git: denied.
- WP5 role workspaces: temporary GitHub Actions artifacts with 30-day retention.
- Compact WP5 execution report: Actions artifact with 90-day retention plus Git execution receipt.
- Canonical Cloudflare R2 mutation: none.
- Release freezing: none.

## Authority still withheld

Release acceptance and freeze, canonical R2 publication, selector activation, validation consumption, active OPT-A-to-OPT-B handoff, OPT-B/C/D market claims, probability, exposure, trading and execution remain unauthorised.

## Next gate

`A2-G2 — operator review of observation construction and quarantine disposition`, followed by `A2-G3 — role release freeze` only if the review passes.

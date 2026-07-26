# OPT-B.C1 v2 B1-G5 — Shadow activation

**Decision: PASS — activate the exact remote-verified Discovery and Development C1 releases as SHADOW derived-fact authorities.**

The B1-G5 packet binds the immutable WP5 publication record, a complete comparison packet, an explicit no-historical-relabelling assertion, the C1-to-C2 interface validation and a tested selector rollback path.

## Selected releases

| Role | Release | Selector | Manifest SHA-256 |
|---|---|---|---|
| Discovery | `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1` | `SHADOW` | `6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2` |
| Development | `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1` | `SHADOW` | `ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017` |
| Validation | Not built | `NONE` | — |

The shadow selector grants read, inspection and comparison authority for exact atomic derived facts only. It does not create an active C2 parent relationship.

## Comparison disposition

- Mathematical golden and fixture comparisons: `EXACT_EQUIVALENCE`.
- C1 cardinality against eligible OPT-A v2 bars: exact after declared quarantine and null policy.
- Historical OPT-A v1 versus OPT-A v2: `NOT_COMPARABLE / SOURCE_LINEAGE_CHANGE`.
- No semantic thresholds, midpoint claims or retrospective relabelling were introduced.
- Unexplained blocking differences: **0**.

## C2 boundary

`C1_TO_C2_HANDOFF_CONTRACT_v0_1` is interface-valid, but C2 consumption remains `DENIED_PENDING_SEPARATE_HANDOFF_REVIEW`. C2 stays `DESIGN_AND_FIXTURES_ONLY`; no C2, C2E, C2.5, C3, OPT-C or OPT-D authority is activated.

## Rollback

The selector transaction is reversible by returning Discovery and Development to `NONE` atomically. The published releases and historical activation record remain immutable. Legacy OPT-B and OPT-A v1 are prohibited rollback targets.

## Retained prohibitions

- Validation remains `LOCKED_UNCONSUMED`.
- Probability, exposure, trading and execution authority remain `NONE`.
- Active OPT-A selectors are unchanged.
- No release bytes were rebuilt, republished or overwritten.

**Resulting state:** `C1_B1_G5_PASS_SHADOW_ACTIVE_C2_DENIED`.

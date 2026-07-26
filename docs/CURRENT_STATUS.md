# Current status

Snapshot date: 26 July 2026.

## Integrated baseline

The reset and OPT-A v2 build line through selector activation are merged into `main`:

- R0 reset: `a9902c97e21131b1882b4c11ca3a2a79273e7c77`
- OPT-A WP1-WP6 and A2-G0 through A2-G5: complete
- A2-G5 selector activation: `fb5b2fea2200b05a050aa1f8af51121a1883a4a5`
- OPT-B.C1 v2 WP1 boundary: `3940f64a635f547a6bef6045bd3a8a27e386dcdd`
- OPT-B.C1 v2 WP2 contract freeze: `fefac25f19a836898c3a22228036cd66617dca07`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and prohibited as a selector, parent or rollback target.

## Active OPT-A v2 role set

| Role | Release | Authority | Selector | Consumption |
|---|---|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `ACTIVE_DISCOVERY` | `ACTIVE` | `NOT_APPLICABLE` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `ACTIVE_DEVELOPMENT` | `ACTIVE` | `NOT_APPLICABLE` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `ACTIVE_VALIDATION` | `ACTIVE` | `LOCKED_UNCONSUMED` |

The **21,410** quarantined derived-bucket records remain bound to `RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS` and cannot become downstream parents.

## OPT-B.C1 v2 WP2

WP2 result: `PASS — CONTRACTS, FORMULAS AND SCHEMAS FROZEN`.

The repository now freezes:

- one atomic C1 record per admissible closed OPT-A v2 bar;
- the exact active OPT-A v2 handoff as the only admissible parent profile;
- `C1.FORMULAS.v0.1` with 18 versioned Decimal formulas;
- exact zero-range, prior-close, gap, mismatch and source-inadmissibility behaviour;
- canonical record, release, manifest, publication approval, selector and supersession schemas;
- a blocking ten-check C1 QA registry;
- 15M and 2H_A_L BID/ASK as the canonical initial scope;
- H1 clocks as control-only and Validation as `LOCKED_UNCONSUMED`;
- C1 release placeholders and all C1 selectors at `NONE`;
- valid and invalid synthetic handoff fixtures for WP3.

WP3 may implement a reference Decimal engine, adapter, deterministic identity and canonical serializer against synthetic/golden fixtures only.

No C1 market replay, local release freeze, R2 publication, selector activation or C2 consumption is authorised.

## Research Operations Foundation RO-G0

RO-G0 result: `PASS — RO-WP1 AUTHORISED AFTER MERGE`.

The preflight pins `main` at `fefac25f19a836898c3a22228036cd66617dca07`, binds the Research Operations implementation plan by SHA-256 `4f0de710ab0157041f57ab781c9411a68aaf211b3b4a41f249978f07b0d580a0`, and freezes:

- `ovc.research_operations` as the canonical future namespace;
- contract, schema, registry, fixture, record, console and derived-runtime path boundaries;
- one-way dependencies from approved OPT-A and optional approved C1/C2 objects;
- metadata-only visibility for Validation while payload access remains denied;
- Git, external-root and rebuildable-index storage separation;
- RO-WP1, RO-WP2 and RO-WP3 predecessor gates.

RO-G0 creates no runtime package, CLI, database, console or research record. After merge, only `RO-WP1 — Evidence envelope and record schemas` may begin.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / REMOTE_VERIFIED` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 role set | `A2_G5_PASS / ACTIVE` | `ACTIVE` |
| OPT-B.C1 v2 | `WP2_CONTRACTS_FROZEN / WP3_FIXTURE_ENGINE_AUTHORISED` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| Research Operations | `RO_G0_PASS / WP1_BUILD_AUTHORISED_AFTER_MERGE` | Not applicable |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

Validation remains `LOCKED_UNCONSUMED`. Research Operations and C1 cannot read the Validation payload, future paths or downstream outcomes without separate exact approvals.

## Parallel next boundaries

- `OPT-B.C1 v2 WP3 — reference engine and fixture trust`
- `RO-WP1 — Evidence envelope and record schemas`

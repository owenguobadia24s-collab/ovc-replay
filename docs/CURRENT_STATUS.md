# Current status

Snapshot date: 26 July 2026.

## Integrated baseline

The reset and OPT-A v2 build line through selector activation are merged into `main`:

- R0 reset: `a9902c97e21131b1882b4c11ca3a2a79273e7c77`
- OPT-A WP1-WP6 and A2-G0 through A2-G5: complete
- A2-G5 selector activation: `fb5b2fea2200b05a050aa1f8af51121a1883a4a5`
- OPT-B.C1 v2 WP1 boundary: `3940f64a635f547a6bef6045bd3a8a27e386dcdd`
- OPT-B.C1 v2 WP2 design freeze: `fefac25f19a836898c3a22228036cd66617dca07`
- OPT-B.C1 v2 WP3 reference engine: `d5c0f1a9053f837ee85e2b478fba0662a133cc29`
- OPT-B.C1 v2 B1-G0 replay approval: `d584813a7a26e7e272259abc87c88b9bb212fc50`
- OPT-B.C1 v2 WP4 candidate replay: `74151d3c9f4659fc6414456c2ad13a138912089c`
- Research Operations RO-G0: `8a4852358324a4e6dfc9f7c239be9e9eb8d69c23`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and prohibited as a selector, parent or rollback target.

## Active OPT-A v2 role set

| Role | Release | Authority | Selector | Consumption |
|---|---|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `ACTIVE_DISCOVERY` | `ACTIVE` | `NOT_APPLICABLE` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `ACTIVE_DEVELOPMENT` | `ACTIVE` | `NOT_APPLICABLE` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `ACTIVE_VALIDATION` | `ACTIVE` | `LOCKED_UNCONSUMED` |

The **21,410** quarantined derived-bucket records remain bound to `RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS` and cannot become downstream parents.

## OPT-B.C1 v2 WP4

WP4 result: `PASS — DISCOVERY AND DEVELOPMENT REPLAY QA COMPLETE; LOCAL CANDIDATE RECORDED`.

Workflow run `30185680001` used only the exact B1-G0-approved Discovery and Development parents. It produced:

| Role | 15M BID | 15M ASK | 2H_A_L BID | 2H_A_L ASK | Total |
|---|---:|---:|---:|---:|---:|
| Discovery | 71,982 | 71,982 | 7,964 | 7,964 | 159,892 |
| Development | 23,853 | 23,853 | 2,583 | 2,583 | 52,872 |

The local candidate contains **212,764** records in **192** compressed files with **36,169,581** candidate bytes. A complete second replay produced an identical inventory, sizes and SHA-256 values.

The candidate artifact is GitHub Actions artifact `8626942276`, digest `sha256:fb52ea4f84fa7c1d79c9c524470d6722ab82b09a5ed4d4f0278fda4d330eabfc`. It is `LOCAL_ONLY / CANDIDATE`, not frozen, published or selected.

WP4 excluded 12,104 Discovery and 4,862 Development quarantined upstream records. It performed no interpolation, gap repair or cross-side substitution. Validation was not downloaded and remains `LOCKED_UNCONSUMED`.

## Research Operations Foundation RO-WP1

RO-WP1 result: `IMPLEMENTED — READY FOR RO-G1 OPERATOR REVIEW`.

The evidence kernel provides:

- a permanent model-optional evidence envelope;
- canonical UTF-8 JSON and deterministic content-derived record IDs;
- ten versioned research record types;
- prospective-cutoff and Validation metadata-only enforcement;
- DRAFT, FROZEN, ADJUDICATED, SUPERSEDED and WITHDRAWN lifecycle rules;
- frozen-record mutation, duplicate-ID and post-cutoff rejection;
- append-only supersession preserving predecessor bytes;
- explicit `REPRODUCIBLE`, `PARTIALLY_AVAILABLE` and `NOT_REPRODUCIBLE` states;
- nine non-authoritative synthetic fixture families and executable integrity tests.

RO-WP1 creates no operator research record, durable write service, CLI, artifact catalogue, QA runner, read model or console. RO-WP2 remains blocked until a separate RO-G1 operator `PASS`.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / REMOTE_VERIFIED` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 role set | `A2_G5_PASS / ACTIVE` | `ACTIVE` |
| OPT-B.C1 v2 | `WP4_REPLAY_QA_PASS / LOCAL_CANDIDATE` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| Research Operations | `RO_WP1_IMPLEMENTED / RO_G1_REVIEW_REQUIRED` | Not applicable |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

Validation remains `LOCKED_UNCONSUMED`. C1 R2 publication, selector activation and C2 consumption remain denied. Research Operations active-research, market, probability, exposure, trading, execution and agent authority remain absent.

## Parallel next boundaries

- `OPT-B.C1 v2 B1-G1 — WP4 candidate inventory and freeze review`
- `RO-G1 — Evidence integrity`

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
- OPT-B.C1 v2 B1-G1 candidate inventory review: `29718a526235ef7268a3226173352951072c35e8`
- OPT-B.C1 v2 WP4F local release freeze: `74af01f611d56b5b4a580543236859ce7767e1fc`
- Research Operations RO-G0: `8a4852358324a4e6dfc9f7c239be9e9eb8d69c23`
- Research Operations RO-WP1: `8944da84dec4915c7d7748ae5dbb2a9e1d187d28`
- Research Operations RO-G1: `51f94c55eaed8c997bc141d33f0f3f4fa452bb0f`
- Research Operations RO-WP2: `62c9a7bf13fce5dd7f3850179c28f89aec16b9ee`
- Research Operations RO-G2: `e19456821e243c6f9fb7f77e49cb5cad295c3d18`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and prohibited as a selector, parent or rollback target.

## Active OPT-A v2 role set

| Role | Release | Authority | Selector | Consumption |
|---|---|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `ACTIVE_DISCOVERY` | `ACTIVE` | `NOT_APPLICABLE` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `ACTIVE_DEVELOPMENT` | `ACTIVE` | `NOT_APPLICABLE` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `ACTIVE_VALIDATION` | `ACTIVE` | `LOCKED_UNCONSUMED` |

The **21,410** quarantined derived-bucket records remain bound to `RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS` and cannot become downstream parents.

## OPT-B.C1 v2 B1-G2

B1-G2 result: `PASS — EXACT WP4F FROZEN RELEASE INVENTORY ACCEPTED; WP5 R2 PUBLICATION AUTHORISED`.

The decision is bound to WP4F workflow run `30187276514` and these exact publication sources:

| Role | Release | Manifest SHA-256 | Record files | Records | Manifest-accounted bytes |
|---|---|---|---:|---:|---:|
| Discovery | `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1` | `6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2` | 144 | 159,892 | 27,451,233 |
| Development | `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1` | `ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017` | 48 | 52,872 | 8,719,477 |
| **Total** | **2 releases** | — | **192** | **212,764** | **36,170,710** |

Both release roots are `RELEASE_FROZEN`, `CANDIDATE`, QA `PASS` and locally full-byte verified. Their GitHub transport artifacts are retained until 24 October 2026; WP5 must consume these exact artifacts or return to a new freeze execution.

B1-G2 authorises only immutable R2 publication of the exact Discovery and Development releases, using payload-first, manifest-last publication followed by full remote byte verification. Publication from rebuilt or substituted bytes is prohibited. Remote collisions, source mismatches or hash failures stop the packet.

C1 selectors remain `NONE`. Selector activation requires a separate post-publication review. C2 consumption remains denied, and Validation remains `LOCKED_UNCONSUMED`.

## Research Operations Foundation RO-G2

RO-G2 result: `PASS — BOUNDED LOCAL OPERATIONS APPROVED; RO-WP3 AUTHORISED FOR BUILD`.

The review confirms:

- complete governed sessions can be produced without manual record editing;
- every public write emits a frozen AuditEvent;
- append-only overwrite, identity reuse, traversal, symlink escape, and deletion attempts fail closed;
- catalogue rebuilds are logically deterministic;
- changed, missing, expired, orphaned, and dependency-defect evidence remains visible;
- Validation remains metadata-only and `LOCKED_UNCONSUMED`;
- no Git, R2, selector, threshold, classification, probability, exposure, execution, or agent side effect is introduced.

The RO-WP2 CLI, append-only service, audit service, catalogue, and queues are approved for bounded local operation. This is not active-research or market authority.

RO-WP3 is authorised for build. Its QA runner, read model, and console are not active.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / REMOTE_VERIFIED` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 role set | `A2_G5_PASS / ACTIVE` | `ACTIVE` |
| OPT-B.C1 v2 | `B1_G2_PASS / RELEASE_FROZEN / LOCAL_VERIFIED / WP5_PUBLICATION_AUTHORISED` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| Research Operations | `RO_G2_PASS / WP2_BOUNDED_LOCAL / WP3_BUILD_AUTHORISED` | Not applicable |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

Validation remains `LOCKED_UNCONSUMED`. C1 selector activation and C2 consumption remain denied. Research Operations active-research, market, probability, exposure, trading, execution and agent authority remain absent.

## Parallel next boundaries

- `OPT-B.C1 v2 WP5 — R2 publication and full remote verification`
- `RO-WP3 — QA runner, read model and console integration`

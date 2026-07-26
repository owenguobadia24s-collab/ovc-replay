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
- Research Operations RO-WP1: `8944da84dec4915c7d7748ae5dbb2a9e1d187d28`
- Research Operations RO-G1: `51f94c55eaed8c997bc141d33f0f3f4fa452bb0f`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and prohibited as a selector, parent or rollback target.

## Active OPT-A v2 role set

| Role | Release | Authority | Selector | Consumption |
|---|---|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `ACTIVE_DISCOVERY` | `ACTIVE` | `NOT_APPLICABLE` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `ACTIVE_DEVELOPMENT` | `ACTIVE` | `NOT_APPLICABLE` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `ACTIVE_VALIDATION` | `ACTIVE` | `LOCKED_UNCONSUMED` |

The **21,410** quarantined derived-bucket records remain bound to `RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS` and cannot become downstream parents.

## OPT-B.C1 v2 B1-G1

B1-G1 result: `PASS — EXACT WP4 CANDIDATE INVENTORY ACCEPTED; DURABLE LOCAL FREEZE AUTHORISED`.

The review is bound to workflow run `30185680001`, candidate artifact `8626942276`, archive SHA-256 `fb52ea4f84fa7c1d79c9c524470d6722ab82b09a5ed4d4f0278fda4d330eabfc` and inventory SHA-256 `39f55e923fa0a8302024f02d862d294ad9d8448fe197a9849ee9ec0f15d4a383`.

Independent full-byte verification confirmed:

| Role | Files | Bytes | Records |
|---|---:|---:|---:|
| Discovery 2021–2023 | 144 | 27,450,668 | 159,892 |
| Development 2024 | 48 | 8,718,913 | 52,872 |
| **Total** | **192** | **36,169,581** | **212,764** |

All 212,764 record IDs are unique. There are zero duplicate record IDs, missing candidate files or payload hash mismatches. The deterministic second replay matched the complete inventory. The 12,104 Discovery and 4,862 Development upstream quarantine records remain excluded, and Validation remains `LOCKED_UNCONSUMED`.

B1-G1 authorises only the controlled promotion of this exact candidate into durable immutable local release roots. It does not claim that the releases are already `RELEASE_FROZEN` or `LOCAL_VERIFIED`; those states require the subsequent freeze execution and post-freeze full-byte verification.

## Research Operations Foundation RO-WP2

RO-WP2 result: `IMPLEMENTED — READY FOR RO-G2 OPERATOR REVIEW`.

The repository now contains:

- `ovc research`, `ovc artifact`, and `ovc queue` command families;
- environment-only configuration and approved portable path aliases;
- derived draft storage and append-only frozen record storage;
- immutable AuditEvent emission for every public write action;
- complete session, observation, claim, realization, adjudication, close and supersession handlers;
- deterministic artifact catalogue scanning and verification;
- changed-byte, missing-file, expired-CI-artifact, orphan-manifest and dependency detection;
- realization, incident, incomplete-session, stale-catalogue and missing-artifact queues;
- Windows launcher and operator guide.

No operator record was created by the build packet. The CLI and catalogue are implemented but not active pending RO-G2. RO-WP3 remains blocked pending RO-G2.

## Active authority matrix

| Boundary | State | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / REMOTE_VERIFIED` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 role set | `A2_G5_PASS / ACTIVE` | `ACTIVE` |
| OPT-B.C1 v2 | `B1_G1_PASS / EXACT_CANDIDATE_FREEZE_AUTHORISED / NOT_YET_FROZEN` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| Research Operations | `RO_WP2_IMPLEMENTED / RO_G2_REVIEW_REQUIRED` | Not applicable |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

Validation remains `LOCKED_UNCONSUMED`. C1 R2 publication, selector activation and C2 consumption remain denied. Research Operations active-research, market, probability, exposure, trading, execution and agent authority remain absent.

## Parallel next boundaries

- `OPT-B.C1 v2 WP4F — durable local release freeze and full-byte verification`
- `RO-G2 — Operating reliability`

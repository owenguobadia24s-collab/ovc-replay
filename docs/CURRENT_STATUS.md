# Current status

Snapshot date: 26 July 2026.

## Integrated baseline

The reset and OPT-A v2 build line through selector activation are merged into `main`:

- R0 reset: `a9902c97e21131b1882b4c11ca3a2a79273e7c77`
- OPT-A WP1-WP6 and A2-G0 through A2-G5: complete
- A2-G5 selector activation: `fb5b2fea2200b05a050aa1f8af51121a1883a4a5`
- OPT-B.C1 v2 WP4 candidate replay: `74151d3c9f4659fc6414456c2ad13a138912089c`
- Research Operations RO-WP1: `8944da84dec4915c7d7748ae5dbb2a9e1d187d28`
- Research Operations RO-G1: `51f94c55eaed8c997bc141d33f0f3f4fa452bb0f`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and prohibited as a selector, parent or rollback target.

## Active OPT-A v2 role set

| Role | Release | Authority | Selector | Consumption |
|---|---|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `ACTIVE_DISCOVERY` | `ACTIVE` | `NOT_APPLICABLE` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `ACTIVE_DEVELOPMENT` | `ACTIVE` | `NOT_APPLICABLE` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `ACTIVE_VALIDATION` | `ACTIVE` | `LOCKED_UNCONSUMED` |

The **21,410** quarantined derived-bucket records remain excluded from accepted downstream parentage.

## OPT-B.C1 v2 WP4

WP4 remains `PASS — DISCOVERY AND DEVELOPMENT REPLAY QA COMPLETE; LOCAL CANDIDATE RECORDED`.

The local candidate contains **212,764** records in **192** compressed files with **36,169,581** candidate bytes. It remains `LOCAL_ONLY / CANDIDATE`, not frozen, published or selected. Validation was not downloaded and remains `LOCKED_UNCONSUMED`.

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
| OPT-B.C1 v2 | `WP4_REPLAY_QA_PASS / LOCAL_CANDIDATE` | `NONE` |
| OPT-B.C2 v2 | `DESIGN_AND_FIXTURES_ONLY` | `NONE` |
| Research Operations | `RO_WP2_IMPLEMENTED / RO_G2_REVIEW_REQUIRED` | Not applicable |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

Validation remains `LOCKED_UNCONSUMED`. Research Operations active-research, market, probability, exposure, trading, execution and agent authority remain absent.

## Parallel next boundaries

- `OPT-B.C1 v2 B1-G1 — WP4 candidate inventory and freeze review`
- `RO-G2 — Operating reliability`

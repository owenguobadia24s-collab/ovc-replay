# Current status

Snapshot date: 26 July 2026.
Repository court-record tip before recovery: `015e57d862f740c4a0e722e611e0dbeadfaad209`.

## Integrated baseline

The reset, OPT-A v2 role-set activation, OPT-B.C1 v2 publication and shadow activation, Research Operations Foundation activation, Research Console v0.3 Overview acceptance, OPT-B.C2 actual-parent reconciliation, and exact OPT-A R2 parent-root recovery are represented by the current court record.

Latest authority and operating records:

- OPT-A v2 A2-G5 selector activation: `fb5b2fea2200b05a050aa1f8af51121a1883a4a5`
- OPT-B.C1 v2 B1-G5 shadow activation: recorded in `docs/releases/opt-b-c1-v2/b1-g5/`
- Research Operations RO-G3 local activation: `516e068ff94b3a43964f221ceface2f01f13d010`
- Research Console RC-G2-v0.3 Overview acceptance: `cd0327e11084d19ce8b51fea67c6cfa3eb00c502`
- OPT-B.C2 v2 C2-G3R actual-parent reconciliation: `fa11546a93f865c26d7cf99f5b5c60156bf50f9b`
- Exact OPT-A Discovery/Development R2 root recovery: workflow run `30209041054`; receipt in `docs/releases/opt-a-v2/recovery/`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and prohibited as a selector, parent, parameter source or rollback target.

## Active OPT-A v2 role set

| Role | Release | Authority | Selector | Consumption |
|---|---|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `ACTIVE_DISCOVERY` | `ACTIVE` | `NOT_APPLICABLE` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `ACTIVE_DEVELOPMENT` | `ACTIVE` | `NOT_APPLICABLE` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `ACTIVE_VALIDATION` | `ACTIVE` | `LOCKED_UNCONSUMED` |

All three releases are remotely verified. The 21,410 quarantined derived-bucket records remain bound to `RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS` and cannot become downstream parents.

The exact active Discovery and Development roots have now also been recovered read-only from canonical R2 and verified against the C2 price-parent contract:

| Role | Manifest-bound objects | Payload bytes | Price files | Recovery verification |
|---|---:|---:|---:|---|
| Discovery | 293 | 155,632,392 | 144 | `PASS_C2_EXACT_PRICE_PARENT_CONTRACT` |
| Development | 101 | 52,762,768 | 48 | `PASS_C2_EXACT_PRICE_PARENT_CONTRACT` |
| **Total** | **394** | **208,395,160** | **192** | **PASS** |

The combined recovered root is retained as GitHub Actions artifact `8633917454` (`opt-a-v2-r2-exact-parent-roots`) until 24 October 2026. It contains `discovery/` and `development/` children in the exact shape required by `--opt-a-release-root`.

## OPT-B.C1 v2

B1-G5 result: `PASS — SHADOW ACTIVATION`.

| Role | Release | Selector | Records | Record files | Manifest SHA-256 |
|---|---|---|---:|---:|---|
| Discovery | `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1` | `SHADOW` | 159,892 | 144 | `6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2` |
| Development | `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1` | `SHADOW` | 52,872 | 48 | `ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017` |
| **Total** | **2 releases** | — | **212,764** | **192** | — |

The exact releases are frozen, QA-passed, remotely verified and selected for read, inspection and comparison as atomic derived facts. Validation C1 is not built. C1-to-C2 interface validation has passed, but active C2 consumption is not implied by C1 shadow selection.

## OPT-B.C2 v2

WP1-WP4 contracts, schemas, registries, fixtures, level/container/relation engines, parallel-state, persistence and transition logic are implemented.

C2-G3R result: `PASS_ACTUAL_C1_AND_EXACT_OPT_A_PRICE_PARENT_ENGINE_TRUST`.

C2 consumes the immutable published C1 primitive record together with the exact manifest-bound OPT-A price row identified by its lineage. The former synthetic embedded-price assumption is superseded. Current-bar primitive reconciliation, rolling range and midpoint derivation, confirmed first-valid swings, containers, relation inventories, five-axis state, gap reset, persistence, transitions and 15M-with-latest-first-valid-2H scope have fixture trust.

The former C2-G4 external-input blocker is resolved at the artifact boundary:

`PASS_EXACT_R2_ROOTS_RECOVERED_AND_FULL_BYTE_VERIFIED`

Workflow run `30209041054` recovered and verified both exact OPT-A roots. Therefore the current C2 position is:

- exact OPT-A parent roots: `RECOVERED_VERIFIED_ARTIFACT_AVAILABLE`
- actual market replay: `NOT_EXECUTED`
- local C2 candidate release: `NONE`
- publication: `NONE`
- selector: `NONE`
- activation: `NONE`

Validation remains `LOCKED_UNCONSUMED`. C2-G4 is now ready for the separately authorised exact-parent replay using the recovered OPT-A artifact and exact C1 roots.

## Research Operations Foundation

RO-G3 result: `PASS`.

`OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.1` is accepted as `ACTIVE_RESEARCH_OPERATIONS_LOCAL`.

Approved bounded local capabilities:

- append-only research record and audit services;
- research CLI, artifact catalogue and queues;
- no-mutation QA runner;
- deterministic, replaceable typed read model;
- multidimensional health projection;
- local static console and optional Streamlit shell on `127.0.0.1`.

The read model and console do not outrank their source records and expose no direct Git, R2, selector, threshold or classification mutation.

## Research Console v0.3

RC-G2-v0.3 result: `PASS`.

The unified shell, context-preserving navigation, Overview workspace and seven-domain ambient-health projection are accepted for bounded local read-only use. The health domains are Data, Read model, Artifacts, QA, Research records, Repository and Semantic.

The Research workspace remains fixture-only pending `RC-WP3-v0.3 — Research workspace, replay, evidence and queue`. Mutating console authority and remote deployment remain denied.

## Active authority matrix

| Boundary | Current state | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / REMOTE_VERIFIED` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 role set | `A2_G5_PASS / ACTIVE / R2_ROOTS_RECOVERED` | `ACTIVE` |
| OPT-B.C1 v2 | `B1_G5_PASS / REMOTE_VERIFIED / SHADOW` | `SHADOW` |
| OPT-B.C2 v2 | `C2_G3R_PASS / EXACT_PARENT_INPUTS_AVAILABLE / REPLAY_NOT_EXECUTED` | `NONE` |
| Research Operations | `RO_G3_PASS / ACTIVE_RESEARCH_OPERATIONS_LOCAL` | Not applicable |
| Research Console v0.3 | `RC_G2_PASS / OVERVIEW_LOCAL_READ_ONLY / WP3_AUTHORISED` | Not applicable |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

## Retained authority boundaries

- Validation consumption remains `LOCKED_UNCONSUMED`.
- C2 market replay has not yet run.
- C2 candidate, publication, selector and activation authority remain absent.
- C2E, C2.5, C3 and new OPT-C/OPT-D authority remain absent.
- Probability, exposure, trading, execution and autonomous-agent authority remain `NONE`.
- Direct UI writes to Git, R2 or the primary branch remain denied.

## Next boundaries

1. Execute `C2_G4_EXACT_PARENT_MARKET_REPLAY` using recovered OPT-A artifact `8633917454` and the exact C1 Discovery/Development roots.
2. Freeze and review a local C2 candidate only if the exact-parent replay and QA pass.
3. Continue `RC-WP3-v0.3 — Research workspace, replay, evidence and queue` under the accepted read-only and fail-closed boundaries.

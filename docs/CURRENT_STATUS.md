# Current status

Snapshot date: 26 July 2026.
Repository court-record tip reviewed: `85d2638d36c5039c35d2d49fcdb499dd48e7b354`.

## Integrated baseline

The reset, OPT-A v2 role-set activation, OPT-B.C1 v2 publication and shadow activation, Research Operations Foundation activation, Research Console v0.3 Overview acceptance, OPT-B.C2 actual-parent reconciliation, and C2-G4 exact-parent Discovery and Development replay are merged into `main`.

Latest authority-changing or boundary-confirming records:

- OPT-A v2 A2-G5 selector activation: `fb5b2fea2200b05a050aa1f8af51121a1883a4a5`
- OPT-B.C1 v2 B1-G5 shadow activation: recorded in `docs/releases/opt-b-c1-v2/b1-g5/`
- Research Operations RO-G3 local activation: `516e068ff94b3a43964f221ceface2f01f13d010`
- Research Console RC-G2-v0.3 Overview acceptance: `cd0327e11084d19ce8b51fea67c6cfa3eb00c502`
- OPT-B.C2 v2 C2-G3R actual-parent reconciliation: `fa11546a93f865c26d7cf99f5b5c60156bf50f9b`
- OPT-B.C2 v2 C2-G4 exact-parent replay: `85d2638d36c5039c35d2d49fcdb499dd48e7b354`

Historical `OPT-A.GBPUSD.2026H1.v1` remains `SUPERSEDED_UNPUBLISHED`, unavailable and prohibited as a selector, parent, parameter source or rollback target.

## Active OPT-A v2 role set

| Role | Release | Authority | Selector | Consumption |
|---|---|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `ACTIVE_DISCOVERY` | `ACTIVE` | `NOT_APPLICABLE` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `ACTIVE_DEVELOPMENT` | `ACTIVE` | `NOT_APPLICABLE` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `ACTIVE_VALIDATION` | `ACTIVE` | `LOCKED_UNCONSUMED` |

All three releases are remotely verified. The 21,410 quarantined derived-bucket records remain bound to `RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS` and cannot become downstream parents.

## OPT-B.C1 v2

B1-G5 result: `PASS — SHADOW ACTIVATION`.

| Role | Release | Selector | Records | Record files | Manifest SHA-256 |
|---|---|---|---:|---:|---|
| Discovery | `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1` | `SHADOW` | 159,892 | 144 | `6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2` |
| Development | `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1` | `SHADOW` | 52,872 | 48 | `ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017` |
| **Total** | **2 releases** | — | **212,764** | **192** | — |

The exact releases are frozen, QA-passed, remotely verified and selected for read, inspection and comparison as atomic derived facts. Validation C1 is not built. C1-to-C2 interface validation has passed; C2-G4 used the exact canonical C1 parents without changing C1 selector authority.

## OPT-B.C2 v2

WP1-WP4 contracts, schemas, registries, fixtures, level/container/relation engines, parallel-state, persistence and transition logic are implemented.

C2-G3R result: `PASS_ACTUAL_C1_AND_EXACT_OPT_A_PRICE_PARENT_ENGINE_TRUST`.

C2-G4 result: `PASS_LOCAL_REPLAY`.

The exact manifest-bound OPT-B.C1 and OPT-A Discovery and Development parent chains passed full-byte verification and completed the bounded C2 replay:

| Role | Input records | Scopes | State records | Transition records | Rejected |
|---|---:|---:|---:|---:|---:|
| Discovery | 159,892 | 6 | 303,856 | 245,752 | 0 |
| Development | 52,872 | 6 | 100,578 | 78,158 | 0 |
| **Total** | **212,764** | **12** | **404,434** | **323,910** | **0** |

The 24 replay outputs total 872,839,722 bytes and remain external in workflow artifact `8634383302` with digest `sha256:b8f993f733aed75e488aa60883f00a53596c15e5cd6c14edb787fc3bc12df62f`.

C2-G4 changed no C2 release authority:

- local C2 candidate release: `NONE`
- publication: `NONE`
- selector: `NONE`
- activation: `NONE`
- probability, exposure, trading and execution: `NONE`

Validation remains `LOCKED_UNCONSUMED`.

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

Research Operations Foundation v0.2 has a branch-local `RO2-G0 PASS_DESIGN_FREEZE` packet. It is design canon only; RO2-WP1 runtime implementation has not begun and requires separate operator instruction.

## Research Console v0.3

RC-G2-v0.3 result: `PASS`.

The unified shell, context-preserving navigation, Overview workspace and seven-domain ambient-health projection are accepted for bounded local read-only use. The health domains are Data, Read model, Artifacts, QA, Research records, Repository and Semantic.

The Research workspace remains fixture-only pending `RC-WP3-v0.3 — Research workspace, replay, evidence and queue`. Mutating console authority and remote deployment remain denied.

## Active authority matrix

| Boundary | Current state | Selector |
|---|---|---|
| Evidence store | `ACTIVE_INFRASTRUCTURE / REMOTE_VERIFIED` | Not applicable |
| OPT-A v1 | `SUPERSEDED_UNPUBLISHED / MISSING` | `NONE` |
| OPT-A v2 role set | `A2_G5_PASS / ACTIVE` | `ACTIVE` |
| OPT-B.C1 v2 | `B1_G5_PASS / REMOTE_VERIFIED / SHADOW` | `SHADOW` |
| OPT-B.C2 v2 | `C2_G4_PASS_LOCAL_REPLAY / NO_CANDIDATE_OR_SELECTOR` | `NONE` |
| Research Operations v0.1 | `RO_G3_PASS / ACTIVE_RESEARCH_OPERATIONS_LOCAL` | Not applicable |
| Research Operations v0.2 | `RO2_G0_PASS_DESIGN_FREEZE / RUNTIME_NOT_STARTED` | Not applicable |
| Research Console v0.3 | `RC_G2_PASS / OVERVIEW_LOCAL_READ_ONLY / WP3_AUTHORISED` | Not applicable |
| C2E / C2.5 / C3 | `DEFERRED` | `NONE` |
| OPT-C / OPT-D | `HISTORICAL_QUARANTINED` | `NONE` |

## Retained authority boundaries

- Validation consumption remains `LOCKED_UNCONSUMED`.
- C2 candidate, publication, selector and activation authority remain absent.
- C2E, C2.5, C3 and new OPT-C/OPT-D authority remain absent.
- Probability, exposure, trading, execution and autonomous-agent authority remain `NONE`.
- Direct UI writes to Git, R2 or the primary branch remain denied.
- RO2-G0 grants design records and validators only; no RO2 runtime package has begun.

## Next boundaries

1. Execute a separate C2 candidate-freeze and QA review only when explicitly authorised.
2. Begin RO2-WP1 runtime implementation only under a separate operator instruction.
3. Continue `RC-WP3-v0.3 — Research workspace, replay, evidence and queue` under accepted read-only and fail-closed boundaries.

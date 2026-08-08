# OC-G6 — Standalone OccurrenceContext Terminal Conformance Gate

**Gate:** `OC-G6`  
**Decision authority:** `OPERATOR_REQUIRED`  
**Programme:** `OVC-OCCURRENCE-CONTEXT`  
**Plan:** `OVC-OCCURRENCE-CONTEXT-IMPLEMENTATION-PLAN-0.1` / v0.1  
**Accepted design:** `OVC-OCCURRENCE-CONTEXT-DESIGN-SPEC-0.1`  
**Operator plan authority:** `OC-G0 PASS`  
**Implementation-plan merge:** `d85d98470ebfd4d2a7a911e5e22b7962e8a1ca6a`  
**Final implementation main:** `0915e492309f6ad3fe20213070bea062a4062dda`  
**Candidate gate branch:** `gate/oc-g6-conformance`  
**Status:** `GATE_READY_PENDING_EXACT_GATE_HEAD_ASSURANCE`  

## Decision presented

Accept **OccurrenceContext v0.1** as the completed, frozen, deterministic **non-structural upstream context contract** produced by the operator-approved implementation programme.

The programme has implemented immutable occurrence/context identity separation, canonical serialization, first-valid chronology, append-only supersession, read-only C2/C2E/calendar/clock adapters, inert typed MCARB reference plumbing, exact consumer manifests, Research Operations read-only projection and adversarial conformance.

The governing invariant remains:

> **OccurrenceContext can describe the circumstances of a structural occurrence, but it cannot change what that structural occurrence historically was.**

A `PASS` at this gate does **not** start C2P, does not activate context as a representation input, and grants no scientific, publication, Validation, probability, risk, exposure or execution authority.

## Completed packet sequence

| Packet | Gate / decision | Final assured evidence | Squash merge |
|---|---|---|---|
| `OC-G0` | operator `PASS` | implementation plan and authority packet | `d85d98470ebfd4d2a7a911e5e22b7962e8a1ca6a` |
| `OC-WP0` | `OC-G1` delegated `PASS` | tests `31275794211`, tiered `31275794200` | `02718698b6dcb1b956ae7a34b767d5148f00aeb9` |
| `OC-WP1` | `OC-G2` delegated `PASS` | tests `31276374939`, tiered `31276374934` | `dd855dce1a1179e5ad1f7738968c924ee68c7dbe` |
| `OC-WP2` | `OC-G3` delegated `PASS` | tests `31276747564`, tiered `31276747566` | `da02c918e4c1ba944b7f08b52198350bf654b674` |
| `OC-WP3` | `OC-G4` delegated `PASS` | tests `31276988458`, tiered `31276988479` | `5c08361dbe41a0146177c95716c02c89ce136ec6` |
| `OC-WP4` | `OC-G5` delegated `PASS` | tests `31277185101`, tiered `31277185154` | `e241a5c236300e25e9ee75d51a7197f6f6f44686` |
| `OC-WP5` | delegated engineering `PASS` | tests `31277661944`, tiered `31277661945`; zero review threads | `0915e492309f6ad3fe20213070bea062a4062dda` |

All packet-level authority deltas after OC-G0 were `NONE`.

## What is implemented

1. **Deterministic identity.** `occurrence_key` derives only from immutable structural-anchor evidence. Context identity is separate and versioned by exact pack/dependency/registry/FVT bindings.
2. **Chronology.** Context first-valid time is the maximum of anchor, populated dependencies, required registry availability and own confirmation time; backdating fails closed.
3. **Structural-history firewall.** Context building never writes to C2/C2E. Enrichment creates successors rather than rewriting prior context. Protected upstream files retain exact pre/post blob identities.
4. **Typed envelope contracts.** Schema, context pack, role map, reason codes and non-activating authority states are separately versioned.
5. **Read-only adapters.** Existing GBPUSD BID/ASK C2 and typed C2E v0.2 evidence may be referenced without source replay or activation. Existing clocks `15M` and `2H_A_L` are bounded references; no new clock/lattice is activated.
6. **Episode-relative context.** Elapsed duration, eligible count, phase and censor/completion evidence require lawful C2E records. Censoring is never fabricated as completion.
7. **MCARB boundary.** Auxiliary records are typed references only. Vectors/embeddings/feature maps are blocked. The production admission registry remains `NO_SCIENTIFIC_ADMISSIONS`.
8. **Consumer boundary.** SRI research, FDI/C2G research, future C2P/C2.5/C3 stubs and Research Operations consume only explicitly declared field paths. Whole-envelope/undeclared consumption fails closed. `REPRESENTATION_INPUT` is absent and denied.
9. **Deterministic rebuild.** Runtime/path/hostname/worker/PID metadata is excluded from semantic identity; dependency/reference inventories are canonicalized.
10. **Validation and exposure firewalls.** Validation occurrence access remains denied and no probability/risk/exposure/execution surfaces exist.

## Acceptance conditions and QA

The terminal QA packet records `PASS_FOR_OPERATOR_CONFORMANCE_REVIEW_PENDING_EXACT_G6_HEAD_ASSURANCE` with all `OC-QA-01` through `OC-QA-16` satisfied and all `OC-F01` through `OC-F16` adversarial fixtures passing.

The exact protected upstream blob inventory at final implementation main is:

- `src/ovc/opt_b/c2/state.py` — `a706af2d27e50865f3148ef2254ebd5f5f662e90`
- `registries/opt_b/c2/C2_SCOPE_REGISTRY_v0_1.yaml` — `6b7dcb87db35cc6d9278dea0d20d6d7f5c7fbfb5`
- `src/ovc/opt_b/c2e_v2/models.py` — `80e05c0ba818e7223029823e20c77fabf39e8bbf`
- `contracts/opt_b/c2e/v0_2/C2E_STREAM_CONTRACT_v0_2.md` — `2fc7cee1e6fcc8ea681f99ac6ca1079f936c80b6`

Those hashes are unchanged from the WP5 baseline inventory. No protected C2/C2E source file is part of the WP5 change set.

Detailed changed-file evidence is materialized in `OC_G6_CHANGED_FILE_INVENTORY.json`. No raw market streams, replay caches or large external artifacts were committed. External artifact list for this programme is empty.

## Warnings and explicit deferrals

These are visible but non-blocking for base v0.1 conformance:

- No separately governed standalone session/A-L boundary registry exists. `CALENDAR_SESSION_BINDINGS_v0_1` therefore remains `NO_ACTIVE_SESSION_BOUNDARY_DEFINITION`; session/A-L fields fail closed as unavailable instead of being guessed.
- `MARKET_CONDITION_VOCABULARY_BINDINGS_v0_1` remains `NO_ACTIVE_VOCABULARY`.
- `AUXILIARY_ADMISSION_REGISTRY_v0_1` remains `NO_SCIENTIFIC_ADMISSIONS`.
- C2E real-source replay/activation remains separately deferred; active C2E and active boundary pack remain none under the controlling C2E court record.
- SFC is not reopened by this programme.

There are **no unresolved blocking defects** in the OccurrenceContext implementation programme.

## Current authority before OC-G6

- OccurrenceContext deterministic repository implementation: `IMPLEMENTED / NON-ACTIVE / NONCANONICAL`.
- Context `REPRESENTATION_INPUT`: `DENIED_BY_DEFAULT`.
- C2/C2E mutation: `DENIED`.
- New instrument/market/side/clock/lattice: `DENIED`.
- C2E real-source replay/activation: `DENIED / DEFERRED`.
- Validation: `LOCKED_UNCONSUMED`.
- MCARB scientific activation: `DENIED`.
- Market-condition scientific vocabulary: `NONE`.
- C2P: `NOT_STARTED / NOT_AUTHORIZED`.
- C2.5/C3 semantic change: `DENIED`.
- Selector/family/semantic/model/theory promotion and canonical/R2 publication: `NONE / DENIED`.
- Probability/risk/exposure/execution/agent-write: `NONE`.

## Proposed authority delta on PASS

Exactly one authority change is proposed:

`OCCURRENCE_CONTEXT_v0_1 = ACCEPTED_FROZEN_NONSTRUCTURAL_UPSTREAM_CONTRACT`

That acceptance means later separately governed programmes may reference the frozen OccurrenceContext contract as **non-identity enrichment**. It grants no automatic consumer dependency, structural feature, family/semantic meaning, MCARB activation, C2P implementation or downstream promotion.

All reserved boundaries listed above remain unchanged.

## Rollback

Rollback is non-destructive: supersede/revert the OccurrenceContext implementation through a later explicit version/decision while preserving the accepted design, OC-G0 operator decision, all packet/gate receipts and immutable upstream evidence. No force-push, deletion or history rewrite is required.

## Recommended decision

**PASS** — accept OccurrenceContext v0.1 as the completed frozen non-structural context contract, provided the exact final OC-G6 branch head passes the complete repository suite, OVC profile assurance, compatibility and merge-readiness checks with zero blocking review threads.

Allowed decisions: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`.

Exact operator command:

`OVC APPROVE OC-G6 PASS`

## Exact work after PASS

1. Record the operator OC-G6 decision against the exact reviewed gate head.
2. Mark the OccurrenceContext implementation programme `COMPLETED` and persist the terminal authority state.
3. Squash-merge the bounded OC-G6 decision/closeout PR into `main` after exact-head checks.
4. Record the terminal merge receipt.
5. Stop the OccurrenceContext programme. **Do not start C2P design or implementation in this programme.**

# PD-G4 — Simple UI and Evidence-Bridge Operative Acceptance

## Gate identity

- Gate ID: `PD-G4`
- Governing plan: `OVC C2 Pattern Discovery and Review Layer v0.3`
- Source SHA-256: `03a4c602026950f3a496f6bf2085c378a62292090d334f3b0ea2f17f6463a0aa`
- Baseline main: `b0798b5535f5fb0276a2b524956c801e278b96d4`
- Candidate branch: `build/pd-wp4-simple-ui-evidence-bridge`
- Prerequisites: `PD-G0`, `PD-G1`, `PD-G2`, `PD-G3` PASS.

## Completed packet

`PD-WP4 — Simple UI and Governed Evidence-Bridge Candidate`

Completed:

- Queue, Candidate Detail and Clusters Streamlit views;
- compact filters, explicit empty states and authority banners;
- exact candidate, fingerprint, cluster and source-lineage projections;
- lightweight OPT-A-bound price strip;
- disabled five-class review form;
- automatic source-object resolution;
- canonical AppendRequest model;
- local-loopback service candidate;
- Ed25519 signer interface with no raw private key in Streamlit;
- session-token and freeze-confirmation controls;
- nonce, sequence, source, cutoff and prohibited-field checks;
- globally idempotent request status;
- atomic evidence plus hash-chained audit transaction;
- non-canonical test mode;
- write authority false by default.

## Current authority

- Pattern Discovery transitions, triggers, controls, novelty shadow, fingerprints and provisional clusters: accepted derived computation.
- Simple UI: candidate local fixture/read operation.
- Evidence bridge implementation: candidate only.
- Canonical Pattern Discovery evidence writes through this bridge: `NONE`.
- Live Pattern Discovery triage: `NONE`.
- Active novelty ranking: `NONE`.
- Semantic, family, archetype, C2E and C3 authority: `NONE`.
- Selector, release, R2, Validation, probability, exposure, trading, execution and agent-write authority: `NONE`.

## Proposed authority delta

Approve the simple local Pattern Discovery review surface and activate the governed bridge for the existing five C2 prospective-evidence record classes under the registered single human operator.

The proposed delta would allow:

1. local review of automatically generated prospective candidate windows;
2. automatic immutable source resolution;
3. explicit operator selection of one accepted evidence class;
4. signed, sequence-controlled, append-only evidence and audit commitment;
5. corrections only through linked superseding records.

It would not allow active novelty ranking, automatic evidence creation, semantic/archetype promotion, C2E/C3, selector/release/R2 mutation, Validation consumption, probability, exposure, trading, execution or agents.

## Why operator approval is required

Although the implementation is bounded and fail-closed, PD-G4 would activate an actual canonical research-write capability and a deferred operator-facing action surface. The assistant may not self-grant that authority.

## Acceptance conditions

- exactly three primary views remain in scope;
- every visible case resolves to immutable sources;
- the price strip uses exact OPT-A lineage and never outruns C2;
- manual canonical ID entry is impossible;
- the write service is disabled before approval;
- request IDs are idempotent;
- nonce, sequence, cutoff and operation mode fail closed;
- evidence and audit commit atomically;
- Streamlit never receives raw private-key material;
- fixture, replay, probability, exposure, trading and execution inputs are rejected;
- real operator efficiency is measured against the declared targets;
- focused, retained and repository-wide tests pass.

## Tests and QA

- QA packet: `docs/releases/pattern-discovery-v0-3/pd-wp4/PD_WP4_QA_PACKET.json`.
- Final workflow IDs, candidate SHA and exact changed-file inventory are pinned after final CI.

## Warnings

- No real prospective candidate has been reviewed through the UI.
- No production operator Ed25519 key has been configured or exposed.
- Fixture signatures prove the boundary and transaction flow only; they are non-canonical.
- Real browser timings and accidental-action observations remain part of the operator acceptance session.
- Approval of PD-G4 does not automatically begin the first real batch unless a lawful prospective source is available.

## Rollback

Disable the bridge by returning `write_authority=false` and remove the Pattern Discovery UI entry from normal operation. Preserve committed evidence, audit events, rejected requests and incidents. No rollback deletes or rewrites canonical evidence.

## Recommended decision

`PASS`, conditional on final CI and the operator accepting the bounded single-operator write model and efficiency evidence.

Other lawful decisions: `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`.

## Exact work after approval

- record the PD-G4 operator decision and operator-key registry binding;
- integrate the bounded packet into main;
- start `PD-WP5` only when `REAL_PROSPECTIVE_SOURCE_AVAILABLE` is satisfied;
- operate the first bounded prospective discovery batch;
- stop again at `PD-G5` for the first batch and any C2E/semantic direction decision.

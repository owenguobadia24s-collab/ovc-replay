# PES VIT Qualification Producer Contract v0.1

**Service:** Persistent Execution Service (PES)  
**Scope:** detached exact-head VIT qualification publication preparation  
**Status:** SHADOW_ONLY_PENDING_SEPARATE_ACTIVATION  
**Authority effect:** NONE

## 1. Purpose

This contract defines the producer-side half of the detached VIT qualification liveness path. It closes the architectural gap identified after PES reconciliation proved that waiting alone cannot help when no authoritative producer publishes the exact-head qualification.

PES remains a liveness and persistence service. VIT remains the qualification authority and SIQ remains the physical integration gateway.

## 2. Authoritative input

PES MUST NOT derive qualification authority from pull-request title, body, labels, comments, branch naming, repository presence, or conversational state.

The producer accepts only one canonical `ovc-pes-vit-qualification-publication-request/v0.1` object issued by an already-authorised owner/executor path. The request MUST bind:

- exact candidate head SHA;
- canonical late-binding VIT payload lineage;
- exact PIP ID;
- exact authority-manifest ID;
- exact dependency-frontier ID;
- durable owner-authority source;
- exact trusted issuer identity; and
- the fixed detached-ledger target and write scope.

The request identity is the canonical SHA-256 of every request field except `request_id`. Any mutation after issuance invalidates the request.

## 3. Producer limitations

The producer MUST NOT:

1. create, infer, widen, replace, or reinterpret programme, packet, VIT, SIQ, GRT, scientific, execution, exposure, writer, merge, or operator authority;
2. construct a new authority manifest or dependency frontier;
3. alter the PIP supplied by the authorised issuer;
4. use PR metadata as decision-bearing lineage;
5. bind physical `main` during qualification;
6. mutate the candidate topic branch;
7. create a payload or renewal commit;
8. write to `main`;
9. merge a pull request;
10. write anywhere except the dedicated detached qualification ledger after a separate activation grant.

## 4. Fixed publication target

The only prospective publication target is:

- branch/ref: `ovc/vit-qualification-ledger-v1`;
- root: `.ovc/vit-qualifications`;
- write scope: `ENVELOPE_AND_EXACT_HEAD_POINTER_ONLY`.

Envelope immutability, content addressing, exact-head/tree validation, head-pointer supersession, and collision behavior remain owned by the existing VIT qualification store.

## 5. WP1 shadow boundary

WP1 implements request validation and exact envelope preparation only.

WP1 does **not** activate:

- detached-ledger writes;
- persistent unattended producer dispatch;
- event subscriptions or polling;
- generic programme admission;
- VIT programme resurrection; or
- any new physical-main capability.

The WP1 command MUST terminate with `PES_VIT_QUALIFICATION_PRODUCER=SHADOW_READY_NO_LEDGER_WRITE` after preparing a valid exact-head envelope.

## 6. Activation preconditions

Any future activation MUST be a separate bounded gate and MUST bind, at minimum:

1. a trusted issuer/executor identity already intersected with current owner authority;
2. a durable request transport independent of PR metadata;
3. ledger-ref-only write authority with fast-forward/content-addressed semantics;
4. fail-closed behavior for unknown programmes, invalid owner authority, stale heads, malformed requests, or target drift;
5. idempotent replay and restartability under PES fencing/liveness semantics;
6. no direct-main, merge, force-push, history-rewrite, or parallel-writer capability; and
7. an explicit rollback that disables new producer dispatch while preserving all ledger evidence.

Until that activation gate passes, the producer remains shadow-only.

## 7. CERS lineage

Historical CERS persistent-supervisor runtime evidence may be reused as implementation lineage for restartability, fencing, and trusted packet-executor mechanics. This does not make PES programme-specific and does not revive a completed VIT programme as a CERS-admitted programme. PES producer activation must be represented as a new bounded infrastructure capability with its own exact write domain.

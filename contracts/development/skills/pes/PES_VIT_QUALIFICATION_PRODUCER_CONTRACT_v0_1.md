# PES VIT Qualification Producer Contract v0.1

**Service:** Persistent Execution Service (PES)  
**Scope:** detached exact-head VIT qualification publication  
**Status:** ACTIVE_BOUNDED_WHEN_ACTIVATION_RECORD_IS_ON_CURRENT_MAIN  
**Authority effect:** BOUNDED_INFRASTRUCTURE_ACTIVATION_ONLY

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

## 3. Permanent limitations

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
10. force-push or rewrite history;
11. subscribe to repository events or poll for work under this activation; or
12. write anywhere except the dedicated detached qualification ledger.

## 4. Fixed publication target

The only active publication target is:

- branch/ref: `ovc/vit-qualification-ledger-v1`;
- root: `.ovc/vit-qualifications`;
- write scope: `ENVELOPE_AND_EXACT_HEAD_POINTER_ONLY`.

Envelope immutability, content addressing, exact-head/tree validation, head-pointer collision behavior, and idempotent replay remain owned by the existing VIT qualification store.

## 5. WP1 shadow boundary

WP1 implemented request validation and exact envelope preparation only. It intentionally did not activate detached-ledger writes or persistent producer dispatch.

That historical shadow boundary remains valid evidence for the implementation stage; it is superseded prospectively only by the exact activation record described below.

## 6. Operator activation

The bounded activation gate is `DSAI3V-PES-VIT-G-PRODUCER-ACTIVATION`.

The only accepted operator grant is:

`OVC APPROVE PES-VIT-QUALIFICATION-PRODUCER ACTIVATION PASS`

The grant activates exactly:

1. publication of an already-validated exact VIT qualification envelope to the fixed detached ledger;
2. creation/update of the exact-head pointer through the existing content-addressed VIT qualification store; and
3. execution from a durable PES dispatch bound to the exact request, activation ID, trusted executor identity, fixed write domain, semantic owner, and current positive fencing generation.

The activation does **not** grant event subscription, polling, generic programme admission, programme semantics, VIT decision authority, SIQ/GRT authority, direct-main write, merge, force-push, history rewrite, scientific authority, market authority, execution authority, or exposure authority.

The durable activation record is:

`docs/releases/development-skills-v0-3/pes-vit-liveness/PES_VIT_QUALIFICATION_PRODUCER_ACTIVATION_PACKET_v0_1.json`

Activation is effective only when that record and its implementation are on current `main`.

## 7. Persistent execution semantics

A producer dispatch MUST be content-addressed and MUST bind:

- the exact canonical owner-issued request ID;
- the exact activation ID;
- the request's trusted issuer/executor identity;
- action `PUBLISH_DETACHED_VIT_QUALIFICATION`;
- write domain `ovc/vit-qualification-ledger-v1:.ovc/vit-qualifications`;
- semantic owner `DSAI_VIT_PHYSICAL_CONTROLLER`; and
- the current positive PES fencing generation.

A stale or mismatched fence MUST fail before the ledger actuator is reached. Replaying the same authorised dispatch is safe because the VIT store is content-addressed and idempotent for the same exact envelope/head binding.

PES may reuse historical CERS fencing, restartability, checkpoint, and durable-dispatch mechanics as implementation lineage. That reuse transfers no CERS programme semantics or programme-specific authority.

## 8. Rollback

Rollback disables new producer publish-mode dispatch while preserving already-published detached qualification evidence and Git history. Rollback MUST NOT delete valid qualification evidence, mutate `main` directly, weaken VIT validation, or rewrite history.

# OC-D0 — Standalone OccurrenceContext Design Review Packet

**Gate:** `OC-D0`  
**Decision authority:** `OPERATOR_REQUIRED`  
**Design:** `OVC-OCCURRENCE-CONTEXT-DESIGN-SPEC-0.1`  
**Baseline:** `main@549b09e6a6e98366db12a07e57bb2d0991c3b6f6`  
**Candidate design branch:** `plan/occurrence-context-v0-1`  
**Status:** `GATE_READY`  
**Authority delta on PASS:** design acceptance only; permits preparation of a separate implementation plan.

## Design decision presented

Accept a standalone OccurrenceContext contract before C2P. The context layer binds immutable occurrence anchors to versioned time/session/calendar/era/clock/scale/parent/auxiliary metadata without changing C2/C2E structural identity or history.

Core firewall:

> OccurrenceContext can describe the circumstances of a structural occurrence, but it cannot change what that structural occurrence historically was.

## Court-record reconciliation

- End-to-end architecture v0.2 REVISED was operator-ratified at `06e657d54afa21670576b181be3f938f2ea01c89`.
- MCARB-D8 PASS is recorded at `00c100ece613bbc5bb8de0c8f8ca45425e036037`; MCARBI terminal closeout is `664b7d2de0c8f475936d857bc929ad1b7eb88421`.
- Current C2E v0.2 main state remains `C2E2-G6-RUN-AUTH / GATE_READY`, with active C2E and active boundary pack `NONE`.
- SFC is `COMPLETED / DEFERRED` after `SFC-G0 DEFER`; standalone OccurrenceContext does not depend on SFC reopening.
- Main contains only a generic SRFD `SRFDOccurrenceContext` object-type allowance, not a standalone forward context service.
- Open PRs #446, #444, #433 and #418 are preserved as proposal/evidence streams and are not imported as main authority.

## Acceptance conditions

PASS should require acceptance of all of the following:

1. `occurrence_key` derives only from immutable structural anchor identity.
2. context versions are independent append-only records with deterministic IDs/hashes.
3. session/date/era/market-condition/MCARB values do not enter structural identity.
4. `REPRESENTATION_INPUT` remains denied by default and requires an exact separately governed RepresentationPack admission.
5. MCARB evidence is referenced by typed ID/hash/version/admission, not copied as mutable vectors.
6. C2/C2E no-mutation is a blocking implementation invariant.
7. future C2P base identity is context-independent.
8. C2.5/C3 must declare field-level context dependencies.
9. Validation remains locked/unconsumed; no occurrence-level Validation context may be constructed under current authority.
10. new instrument/clock/side, scientific MCARB activation, selector/family/semantic/publication or exposure authority remain separately reserved.

## Proposed implementation handoff

If `OC-D0 PASS`, the next artifact is:

**OVC Standalone OccurrenceContext Implementation Plan v0.1**  
Plan ID: `OVC-OCCURRENCE-CONTEXT-IMPLEMENTATION-PLAN-0.1`

Recommended implementation sequence:

`OC-WP0` source/court-record reconciliation -> `OC-WP1` contracts/schema/registries -> `OC-WP2` deterministic envelope builder -> `OC-WP3` C2E/session/clock adapters -> `OC-WP4` MCARB reference extension -> `OC-WP5` adversarial QA/read-only integration -> `OC-WP6` terminal conformance before C2P.

Base implementation plan would use operator-required `OC-G0` and terminal `OC-G6`; bounded build/test gates between them are auto-ratifiable only while their authority delta remains entirely non-reserved.

## Authority after PASS

- OccurrenceContext design: `ACCEPTED`.
- OccurrenceContext implementation: `NONE` until a later implementation plan is ratified.
- C2P: `NOT_STARTED`.
- C2/C2E/SRI/FDI/MCARB semantics: unchanged.
- Validation: `LOCKED_UNCONSUMED`.
- Context structural input: denied by default.
- Selector/family/semantic/publication/probability/risk/exposure/execution: none.

## Rollback

Reject/defer/quarantine the design branch/PR without modifying main. No runtime or scientific state has changed.

## Allowed operator decisions

`PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`.

## Recommended decision

`PASS` — design-only. Do not start C2P.

Exact command:

`OVC APPROVE OC-D0 PASS`

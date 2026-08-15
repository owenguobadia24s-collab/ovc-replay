# RCCR Capability Binding and Frontier Contract v0.1

Status: IMPLEMENTED INACTIVE / NON-AUTHORITATIVE RCCR SYNTHESIS ONLY.

## Exact owner binding

A capability enters an RCCR frontier only through an exact `capability_id`, one owner programme, an owner-state digest, first-valid time and exact provenance references. Missing owner state is unresolved; it is never inferred from a package name, active-stack projection, implementation presence or nearby documentation.

## Six orthogonal maturity planes

Every resolved capability preserves these planes independently:

- design: `YES | NO | UNKNOWN`
- implementation: `YES | PARTIAL | NO | UNKNOWN`
- availability: `YES | NO | UNKNOWN`
- qualification: `QUALIFIED_FOR_DECLARED_USE | NOT_QUALIFIED | UNKNOWN`
- authority: `AUTHORISED_FOR_DECLARED_USE | NOT_AUTHORISED | UNKNOWN`
- activation: `ACTIVE_FOR_DECLARED_USE | INACTIVE | UNKNOWN`

No plane implies another. In particular, implementation may be `YES` while authority is `NOT_AUTHORISED`, activation is `INACTIVE`, or the active-stack classification is `NON_EVALUABLE`.

## Relevant dependency frontier

`ResearchCapabilityFrontier` includes only capability bindings relevant to the frozen requirement/scope. Unrelated repository-main movement and unrelated capability records do not alter logical frontier identity. Owner-state changes that affect a relevant binding do alter identity.

## Owner/projection discrepancy

Active-stack or cross-programme projections are evidence, not owner truth. If an exact projection conflicts with the owner-bound classification, RCCR preserves both and emits `OWNER_STACK_PROJECTION_DISCREPANCY` with `PRESERVE_BOTH_STOP_INFERENCE`. It does not silently reconcile or promote either view.

## Protected and authority boundaries

Validation/protected capability sources are denied before content resolution. Authority bindings may only be carried as owner evidence and must have `authority_effect=NONE` within RCCR. `DMRPI-GREAL-EC1` remains `NONE`; RCCR cannot activate real-source EC1, Path-2, a layer, selector, candidate, theory, method, publication, probability, risk, exposure, trading, execution or agent-write authority.

## Determinism and history

Bindings and frontier rows are canonically ordered. Historical frontiers are append-only and remain addressable when a capability changes. Refresh creates a new frontier generation; it never rewrites prior maturity state.

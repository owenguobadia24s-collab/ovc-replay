# SHSI-WP0 — Stage-0 Court-Record Materialisation

Plan: `OVC-SHARED-SYSTEMS-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-R1`  
Gate: `SHSI-G0B`  
Baseline: `bf0d28812ab2466340ee7af059470bf57c085b87` / tree `f7451a63468154e96d5cb7e91968b9c4d3947641`  
Authority: `AUTO_EXECUTABLE_WITHIN_SHSI-AE-v0.2-R1`; delta `NONE`.

## Materialised

- exact ratified design and plan byte identities;
- G0A operator decision binding;
- exact current GRT SharedServiceBinding generation and one-owner currentness proof;
- executable B0-B6 bootstrap graph and standard-library-only Stage-0 validator;
- deterministic canonical proof hash and cold-run round-trip evidence;
- fail-closed owner-conflict, generation-tamper, cycle/back-edge and missing-authority fixtures;
- explicit inactive/reference-only package authority boundary;
- reuse register and programme-owned state;
- native Programme Genesis exclusion to prevent legacy migration inference;
- late-bound PIP/VIT/SIQ integration lineage.

## Current-main reconciliation

Historical PR #978 began before the repository's late-binding VIT integration contract and later became an unbounded diff after lawful main reconciliation. It is preserved as historical evidence and superseded by this clean current-main requeue. The logical Stage-0 semantics, G0A authority envelope and GRT owner binding are unchanged. Physical main is not embedded in the logical dependency frontier; final placement is resolved by VIT in the one-writer integration lane.

WP0 creates no steady-state Shared Systems service, registry resolver, consumer binding, domain write, scientific authority, source role, Validation access, publication, exposure or execution authority.

## Acceptance

Local targeted assurance: PASS 10 tests on the retained Stage-0 machinery. Current repository Linux assurance, parity, FINAL_HEAD, VIT/SIQ/GRT and exact-final merge readiness remain required before delegated G0B completion.

## Rollback

Before merge, preserve/close the branch. After merge, correct forward by superseding WP0-derived records. G0A, GRT binding, design/plan identities and historical court records remain immutable.

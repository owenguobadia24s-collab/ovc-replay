# SHSI-WP0 — Stage-0 Court-Record Materialisation

Plan: `OVC-SHARED-SYSTEMS-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-R1`  
Gate: `SHSI-G0B`  
Baseline: `e4084161c2656d9d61144feb9ad979a44e4671f4` / tree `ec93154116685e3930f23141e5d9c702bd0045e7`  
Authority: `AUTO_EXECUTABLE_WITHIN_SHSI-AE-v0.2-R1`; delta `NONE`.

## Materialised

- exact ratified design and plan byte identities;
- G0A operator decision binding;
- exact current GRT SharedServiceBinding generation and one-owner currentness proof;
- executable B0-B6 bootstrap graph and standard-library-only Stage-0 validator;
- deterministic canonical proof hash and cold-run round-trip evidence;
- fail-closed owner-conflict, generation-tamper, cycle/back-edge and missing-authority fixtures;
- reuse register and programme-owned state;
- native Programme Genesis exclusion to prevent legacy migration inference;
- PIP/VIT/SIQ integration lineage.

WP0 creates no steady-state Shared Systems service, registry resolver, consumer binding, domain write, scientific authority, source role, Validation access, publication, exposure or execution authority.

## Acceptance

Local targeted assurance: PASS 10 tests. Permanent repository Linux assurance and exact-final SIQ remain required before delegated G0B completion.

## Rollback

Before merge, preserve/close the branch. After merge, correct forward by superseding WP0-derived records. G0A, GRT binding, design/plan identities and historical court records remain immutable.

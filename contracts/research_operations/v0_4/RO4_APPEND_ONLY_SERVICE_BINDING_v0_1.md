# RO4 Append-Only Service Binding v0.1

Status: `IMPLEMENTED_DISABLED_PENDING_RO4_G4`

Plan: `OVC-RESEARCH-OPERATIONS-FOUNDATION-v0.4-C2-STATE-SEQUENCE-EVIDENCE-IMPLEMENTATION-PLAN-0.2`

The RO4 v0.1 record adapter binds the named boundary, friction and prospective-review record types to the accepted Research Operations v0.1 deterministic identity, immutable freeze, exclusive-create storage, audit and supersession services.

Canonical append is disabled until the operator records `RO4-G4 PASS` and enables the exact registry entry in a new commit. Synthetic fixture tests may inject `SYNTHETIC_TEST_ONLY` authority; the production CLI cannot.

## Named records

- `RO4_SEQUENCE_BOUNDARY_ANNOTATION.v0.1`
- `RO4_C2E_FRICTION_RECORD.v0.1`
- `RO4_PROSPECTIVE_SEQUENCE_REVIEW.v0.1`
- `RO4_SIGNATURE_CONCENTRATION_ACKNOWLEDGEMENT.v0.1` only when the diversity audit requires it

## Binding laws

- Exact source release, sequence, manifest where applicable, member IDs and first-valid chronology are required.
- Every source first-valid time must be at or before the admissible cutoff.
- Records are frozen and content-addressed; an exact retry returns the existing record and creates no duplicate.
- Corrections create a successor whose lineage points to the immutable predecessor.
- Every first append and supersession emits a frozen audit event.
- C2 mutation, Pattern Discovery population write, semantic/family promotion, C2E opening, Validation consumption, probability, exposure and execution remain denied.
- Console write controls remain prohibited and require a separate RC-G5A plan and operator gate.

## Rollback

Disable the authority registry in a new commit. Preserve all records and audit events. Do not delete, edit or rewrite any frozen record.

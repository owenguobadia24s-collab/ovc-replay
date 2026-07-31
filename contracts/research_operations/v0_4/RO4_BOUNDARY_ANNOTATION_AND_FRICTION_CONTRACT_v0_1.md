# RO4 Boundary Annotation and C2E Friction Contract v0.1

Status: `PROPOSED_AT_RO4_G0`

Plan: `OVC-RESEARCH-OPERATIONS-FOUNDATION-v0.4-C2-STATE-SEQUENCE-EVIDENCE-IMPLEMENTATION-PLAN-0.2`

Implementation, schemas and synthetic fixtures may exist before RO4-G4, but canonical append is disabled. RO4-G4 is operator-required.

After PASS, only these named record types may be created through the accepted Research Operations v0.1 append-only transaction and audit service:

- `RO4_SEQUENCE_BOUNDARY_ANNOTATION.v0.1`
- `RO4_C2E_FRICTION_RECORD.v0.1`
- `RO4_PROSPECTIVE_SEQUENCE_REVIEW.v0.1`
- exact concentration acknowledgement when required

Boundary annotations bind operator, exact sequence/release/manifest/clock/side/member IDs, operation mode, cutoff and first-valid chronology. Allowed annotation codes are `PROPOSED_START`, `PROPOSED_END`, `CONTINUATION`, `SPLIT`, `MERGE`, `UNCERTAIN`, `NOT_A_SEQUENCE`. Corrections supersede; no in-place edit.

Allowed friction reasons are frozen in `RO4_FRICTION_REASON_REGISTRY_v0_1`. Friction is evidence about a research task and never a C2 mutation, episode, semantic label or automatic C2E approval.

Console write controls remain outside RC-G5 and require a separate RC-G5A implementation plan and operator gate.

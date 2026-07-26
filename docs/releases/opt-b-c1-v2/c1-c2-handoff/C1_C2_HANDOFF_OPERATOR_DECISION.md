# OPT-B.C1 v2 — C1 → C2 handoff review and active activation

**Decision: PASS — exact C1 releases activated and bounded C2 build/replay consumption authorised.**

The exact remote-verified Discovery and Development C1 releases previously selected as SHADOW at B1-G5 are promoted to their role-specific active authorities:

- Discovery: `ACTIVE_DISCOVERY`
- Development: `ACTIVE_DEVELOPMENT`
- Validation: `NONE` and `LOCKED_UNCONSUMED`

The handoff review passed exact release identity, parent OPT-A lineage, record-schema compatibility, all 18 formula-version bindings, first-valid chronology, explicit null and quality states, role/clock/side alignment, no-repair and no-reverse-write requirements.

C2 may use the approved Discovery and Development C1 releases only for its separately gated build and market-replay scope. This decision does not activate a C2 selector, approve C2 semantics, unlock Validation, or create probability, exposure, trading or execution authority.

Rollback atomically returns all C1 role selectors to `NONE` while preserving published releases, manifests and the complete decision history. Historical OPT-B and OPT-A v1 are prohibited rollback targets.

**Next gate:** `OPT-B.C2 v2 WP1 — boundary and implementation registry`.

# ASOCSI WP8 — Session 1 — Stage 1 operator guide

Review the complete 25-case `SOURCE_C1_FIDELITY` packet and return one completed JSON file.

## Bound artifacts

- Reveal packet: `ASOCSI_WP8_S01_STAGE1_REVEAL_PACKET_v0_1.json`
- Reveal packet SHA-256: `5ae775fd5ac9ad5afcecec4f57f3b3fb4fdb5d1d25e2a8d1d9769fde1c52f5c7`
- Human-input template: `ASOCSI_WP8_S01_STAGE1_HUMAN_INPUT_TEMPLATE_v0_1.json`
- Template SHA-256 before operator edits: `607b1d48137b01f3cbb9ea7ae737382fe6ee152497e412fcb725b6ae635b9c9b`
- Governing judgement schema: `schemas/research_operations/asocs/asocs_stage1_fidelity_judgement_v0_1.schema.json`

## Complete the one template

Do not add, remove, duplicate, substitute, or reorder cases. Do not alter the session, stage, reveal-packet hash, presentation ordinals, case IDs, predecessor blind hashes, review-unit IDs, judgement schema, or the fixed construct-survival prohibition.

For every case, replace the incomplete human fields using only the governing Stage-1 schema:

- `fidelity_disposition`: `PASS_FIDELITY`, `MATERIAL_MISMATCH`, `SOURCE_LIMITED`, or `INDETERMINATE`
- `observational_correspondence`: a non-empty human-authored string
- `prior_bridge_disposition`: `VALID`, `INVALID_SOURCE_GAP`, `NOT_APPLICABLE`, or `INDETERMINATE`
- `semantic_leakage`: `NONE`, `PRESENT`, or `INDETERMINATE`
- `traceability`: `PASS`, `FAIL`, or `INDETERMINATE`
- `information_gap_disposition`: `NOT_INFORMATION_GAP`, `INFORMATION_GAP`, or `INDETERMINATE`
- `notes`: optional human-authored text; it may remain an empty string
- `construct_survival_decision`: leave fixed as `PROHIBITED_DURING_CASE_REVIEW`

Evaluate information gaps before assigning failure ownership. A source limitation is not automatically an upstream semantic failure. Case 19 is the frozen `SOURCE_GAP` review unit and exposes its source-limited C1 disposition directly.

Do not recompute C1 formula arithmetic. Machine QA has already bound the displayed C1 payloads to the exact frozen trace artifact.

Return the single completed Session-1 Stage-1 human-input JSON. No Stage-2 case evidence has been constructed or revealed.

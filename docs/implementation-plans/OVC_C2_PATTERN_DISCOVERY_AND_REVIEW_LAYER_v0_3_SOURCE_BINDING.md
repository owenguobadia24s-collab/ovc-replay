# OVC C2 Pattern Discovery and Review Layer v0.3 — Source Binding

## Governing source

- Source document: `OVC_C2_Pattern_Discovery_and_Review_Layer_v0_3_Final_Revised_Implementation_Plan.docx`
- Document version: `0.3`
- Prepared: `2026-07-27`
- SHA-256: `03a4c602026950f3a496f6bf2085c378a62292090d334f3b0ea2f17f6463a0aa`
- Byte length: `60117`
- Repository: `owenguobadia24s-collab/ovc-replay`
- Execution baseline: `3c0785ddb571a4af6de4bf5756a1dfae7e2d3557`
- Execution branch: `build/pd-00-pattern-discovery-v0-3-freeze`

The original DOCX remains the operator-supplied governing source. This repository record binds that immutable source identity to the implementation programme. Any replacement plan requires a new source hash, version and supersession decision.

## Programme purpose

Build a Research Operations layer that reads the active C2 Discovery stream, extracts first-valid transitions, opens deterministic candidate windows, generates trigger and completed fingerprints, assesses novelty and similarity, creates provisional clusters and presents a small human review queue through a simple local UI.

## Authority boundary

This programme may create derived, replaceable research indexes and bounded human-review actions. It may not change canonical C2 records, activate C2E/C2.5/C3, consume Validation, use outcomes in selection, create probability or exposure claims, mutate selectors or releases, write R2 objects, or grant execution authority.

## Work packets

1. `PD-00` — authority and design freeze.
2. `PD-WP1` — transition and candidate-window engine.
3. `PD-WP2` — trigger, novelty and control sampling.
4. `PD-WP3` — fingerprints, similarity and provisional clustering.
5. `PD-WP4` — simple UI and governed evidence bridge.
6. `PD-WP5` — first prospective discovery batch.

## Gate sequence

- `PD-G0` design freeze.
- `PD-G1` transition and candidate-window acceptance.
- `PD-G2` trigger, control and novelty-calibration acceptance.
- `PD-G3` fingerprint and deterministic clustering acceptance.
- `PD-G4` simple UI and evidence-bridge operative acceptance.
- `PD-G5` first real batch review.

Execution under this branch stops at `PD-G0`, because passing that gate changes the programme from design freeze to implementation authority for `PD-WP1`.
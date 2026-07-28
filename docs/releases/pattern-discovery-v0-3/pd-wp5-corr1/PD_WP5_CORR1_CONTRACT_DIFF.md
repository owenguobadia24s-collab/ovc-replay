# PD-WP5-CORR1 — Exact Contract Delta

## Baseline

- Review input: `ovc-pd-wp5-pilot-review-input/v1`
- Review receipt: `ovc-pd-wp5-pilot-review-receipt/v1`
- Defect ledger: `ovc-pd-wp5-pilot-defect-ledger/v1`

The v1 input required candidate ID, disposition, notes and `ui_friction_codes`. It did not conditionally require structured evidence for any non-accepted disposition.

## Candidate v2 delta

The v2 input retains all v1 identity and disposition fields and adds fail-closed conditional requirements:

| Disposition | Newly required evidence |
|---|---|
| `WORKFLOW_ACCEPTED` | acceptance basis, acceptance criteria, evidence references |
| `FLAG_WORKFLOW_DEFECT` | `PD-WF-*` code, component, actual/expected behaviour, reproduction, acceptance criteria, evidence references |
| `FLAG_UI_FRICTION` | non-empty `PD-UI-*` codes, Console surface, component, actual/expected behaviour, reproduction, acceptance criteria, evidence references |
| `DEFER_PILOT_OBJECT` | `PD-DEFER-*` code, resolution criteria, next lawful review condition, evidence references |
| `REJECT_PILOT_OBJECT` | `PD-REJECT-*` code, structural/workflow basis, evidence references |

Unknown, incomplete, duplicated or mismatched decisions are rejected before signing.

## Presentation delta

`Candidate Detail / Review action candidate` now displays disposition-specific structured fields under the banner:

`PD-WP5-CORR1 · STRUCTURED REVIEW ONLY · C2 AND CANONICAL AUTHORITY UNCHANGED`

The evidence freeze button remains governed by existing authority and is disabled for Pilot Discovery.

## Evidence delta

The signed v1 receipt and defect ledger are unchanged. `PD_WP5_CORR1_CORRECTION_LEDGER.json` is a separate deterministic overlay bound to their exact file hashes.

## Computation and authority delta

No change to:

- C2 states or semantics;
- trigger evaluation;
- candidate-window construction;
- queue caps or suppression;
- fingerprints, distance weights or clustering;
- source, release or selector bindings;
- pilot operation count;
- canonical, semantic, family, probability, risk, exposure or execution authority.

The correction recommends `NOT_REQUIRED` for a second replay because all defects concern review validation and evidence presentation and are reproducible against the preserved projection. No replay is authorised.

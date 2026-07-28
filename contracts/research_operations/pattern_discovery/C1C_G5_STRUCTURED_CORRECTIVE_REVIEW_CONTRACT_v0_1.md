# C1C-G5 Structured Corrective Review Contract v0.1

## Status

`FROZEN_NON_ACTIVATING_IMPLEMENTATION_CONTRACT`

## Purpose

This contract governs a structured v2 operator re-review of the immutable corrective Pilot Discovery run:

- run: `PD.PILOT.RUN.96c16f11717e787f971851ee`;
- namespace: `PD.PILOT.GBPUSD.20260622_20260625.v2`;
- authority gate: `C1C-G5`;
- active C2 release: `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2`;
- active C2 manifest: `MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1`;
- selector: `SELECTOR.OPT-B.C2.GBPUSD.v2`.

The machine run, output manifest, candidate identities and original signed v1 operator review are immutable. This packet does not execute another market replay and does not alter any source or derived object.

## Required review contract

The replacement review must use `ovc-pd-wp5-pilot-review-input/v2` and cover the exact six queue candidates from the preserved v1 receipt.

Every decision requires non-empty notes and exact evidence references.

Disposition-specific requirements:

- `WORKFLOW_ACCEPTED`: acceptance basis and acceptance criteria;
- `FLAG_WORKFLOW_DEFECT`: a `PD-WF-*` code, affected component, actual and expected behaviour, reproduction steps and acceptance criteria;
- `FLAG_UI_FRICTION`: a `PD-UI-*` finding code, at least one `PD-UI-*` friction code, affected component and Console surface, actual and expected behaviour, reproduction steps and acceptance criteria;
- `DEFER_PILOT_OBJECT`: a `PD-DEFER-*` code, objective resolution criteria and next lawful review condition;
- `REJECT_PILOT_OBJECT`: a `PD-REJECT-*` code and non-semantic structural basis.

Placeholder text, empty required strings and empty required lists are invalid. Review finalisation must fail closed.

## Evidence handling

The original signed v1 review remains preserved as superseded review evidence. The structured v2 finaliser writes only to a new `operator-review-v2` directory and refuses overwrite.

The v2 finaliser must produce:

1. `pilot-review-receipt-v2.json`;
2. `pilot-defect-ledger-v2.json`;
3. `signed-structured-review-evidence-inventory.json`;
4. `c1c-g5-corrective-pilot-review-gate-input.json`.

The receipt and evidence inventory must be signed with the exact registered Ed25519 operator key and verified immediately using the `ovc-rps` SSHSIG namespace.

## Authority boundary

This contract grants no canonical Discovery processing or append authority. It grants no semantic, family, candidate, threshold, model, novelty, selector, release, R2, Validation, probability, risk, exposure, trading, execution, autonomous-processing or agent-write authority.

The next authority decision remains `C1C-G5-CORRECTIVE-PILOT-REVIEW`. A structured re-review does not itself close that gate.

## Rollback

Preserve the immutable v2 machine run and all signed v1 evidence. Remove or disregard only the unmerged implementation packet. Never delete, rewrite or relabel existing pilot evidence.

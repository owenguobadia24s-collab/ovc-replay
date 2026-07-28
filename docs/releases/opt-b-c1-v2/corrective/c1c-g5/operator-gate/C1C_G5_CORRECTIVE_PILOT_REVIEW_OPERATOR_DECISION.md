# C1C-G5 Corrective Pilot Review — Operator Decision

- Gate: `C1C-G5-CORRECTIVE-PILOT-REVIEW`
- Programme: `OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1`
- Decision: **DEFER**
- Decision authority: **OPERATOR**
- Operator command: `OVC APPROVE C1C-G5-CORRECTIVE-PILOT-REVIEW DEFER`
- Decision date: `2026-07-28`

## Accepted evidence

The operator accepts the exact identity, lineage, deterministic machine replay, structured v2 review completion, file-hash chain and Ed25519 SSHSIG verification bound to:

- pilot run `PD.PILOT.RUN.96c16f11717e787f971851ee`;
- namespace `PD.PILOT.GBPUSD.20260622_20260625.v2`;
- C2 release `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2`;
- C2 manifest `MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1`;
- selector `SELECTOR.OPT-B.C2.GBPUSD.v2`.

No second machine replay is required or authorised.

## Reason for DEFER

The six-object review contains one accepted object, one workflow defect, one UI-friction finding, two deferred objects and one rejected object. Five findings remain recorded and `contract_changes_required=true`.

The unresolved conditions are:

- `PD-WF-STRUCTURED-REVIEW-EVIDENCE-MISSING-001`;
- `PD-UI-STRUCTURED-REVIEW-CONTEXT-MISSING-001`;
- `PD-DEFER-REVIEW-EVIDENCE-INCOMPLETE-001`;
- `PD-DEFER-STRUCTURAL-COMPARISON-PENDING-002`.

A PASS would conceal unresolved workflow, presentation and review conditions.

## Authorised continuation

Only `C1C-G5-CORR2` is authorised. It may:

1. add disposition-specific structured evidence fields to the read-only Console review surface;
2. expose exact evidence-reference resolution for queue, candidate-detail and fingerprint context;
3. prepare and accept operator-local re-review of only the two deferred objects without another machine replay;
4. preserve the accepted and rejected decisions, immutable machine run and all signed evidence;
5. return a final closure packet to `C1C-G5-CORRECTIVE-PILOT-REVIEW`.

## Retained authority boundary

The pilot remains `PILOT_ONLY`, `NON_PROMOTABLE` and excluded from canonical Discovery. No canonical processing or append, semantic/family/candidate/novelty/model/threshold promotion, selector or release mutation, R2 publication, Validation consumption, probability, risk, exposure, trading, execution or agent-write authority is granted.

## Rollback

Preserve all signed evidence and the immutable machine run. Revert only this decision record and bounded CORR2 changes through new non-destructive commits. Do not delete, rewrite, relabel, publish, append or promote any pilot object.

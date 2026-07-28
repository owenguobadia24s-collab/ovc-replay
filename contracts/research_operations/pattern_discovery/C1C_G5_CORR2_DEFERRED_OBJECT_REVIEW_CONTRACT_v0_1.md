# C1C-G5 CORR2 Deferred-Object Review Contract v0.1

## 1. Authority

This contract is governed by the operator decision:

`OVC APPROVE C1C-G5-CORRECTIVE-PILOT-REVIEW DEFER`

It authorises only the bounded, non-activating packet `C1C-G5-CORR2`.

## 2. Exact scope

CORR2 may:

1. add disposition-specific structured evidence fields to the read-only Pattern Discovery Console review surface;
2. resolve exact queue, candidate-detail, fingerprint and source-lineage evidence references;
3. prepare and sign a second human review of exactly the two deferred pilot objects;
4. preserve every non-deferred structured-v2 decision and every immutable signed machine/review artifact;
5. generate a final closure input for `C1C-G5-CORRECTIVE-PILOT-REVIEW`.

The exact deferred objects are:

- `PDPILOT-CANDIDATE-4f41e21b6cd075e0fdbc40e4` — `PD-DEFER-REVIEW-EVIDENCE-INCOMPLETE-001`;
- `PDPILOT-CANDIDATE-bab63b935155e4d9033aed81` — `PD-DEFER-STRUCTURAL-COMPARISON-PENDING-002`.

## 3. No machine replay

CORR2 does not execute another market replay, recompute C1/C2, regenerate candidates, modify fingerprints or rebuild clusters. The accepted deterministic machine run remains:

`PD.PILOT.RUN.96c16f11717e787f971851ee`

A second machine replay is `DENIED_NOT_REQUIRED`.

## 4. Exact evidence-reference resolution

For each deferred object, the review surface and local finalizer must expose and bind at least these exact references:

- `review/queue-items.jsonl#candidate_window_id=<ID>`;
- `review/console-bundle.json#candidate_details.<ID>`;
- `derived/fingerprints.jsonl#candidate_window_id=<ID>`;
- `review/console-bundle.json#candidate_details.<ID>.source_lineage`.

A review cannot close or re-defer an object if any required reference is absent, unresolved or points to another candidate.

## 5. Disposition-specific evidence

The local CORR2 review accepts only:

- `WORKFLOW_ACCEPTED` with closure basis and acceptance criteria;
- `DEFER_PILOT_OBJECT` with a `PD-DEFER-*` code, objective resolution criteria and next lawful review condition;
- `REJECT_PILOT_OBJECT` with a `PD-REJECT-*` code and non-semantic structural/workflow basis.

Every disposition requires non-empty notes and the exact evidence references in Section 4.

## 6. Preservation law

The four non-deferred structured-v2 decisions are immutable inputs. CORR2 must bind their canonical hash and candidate identities in the signed closure evidence. It may not alter the accepted object, workflow-defect object, UI-friction object or rejected object.

The original machine run, output manifest, signed v1 review, structured-v2 review, defect ledgers and evidence inventories remain append-only evidence.

## 7. Final gate recommendation

The generated closure input may recommend `PASS` only when:

- the two deferred objects are no longer deferred;
- exact evidence references resolve;
- CORR2 implementation checks close the workflow-evidence and Console-context findings;
- signature and hash verification passes;
- all retained authority denials remain intact.

Otherwise the recommendation must remain `DEFER` or `BLOCK` as determined by the unresolved conditions.

## 8. Retained prohibitions

CORR2 grants no canonical Discovery processing or append, semantic/family/candidate/novelty/model/threshold promotion, selector or release mutation, R2 publication, Validation consumption, probability, risk, exposure, trading, execution, autonomous processing or agent-write authority.

The pilot remains `PILOT_ONLY`, `NON_PROMOTABLE` and excluded from canonical Discovery.

## 9. Rollback

Revert only CORR2 code, schemas, tests and court records through new non-destructive commits. Preserve every signed external artifact and the immutable machine run. Deletion, history rewriting, identity reuse, relabelling, publication, append and promotion are prohibited.

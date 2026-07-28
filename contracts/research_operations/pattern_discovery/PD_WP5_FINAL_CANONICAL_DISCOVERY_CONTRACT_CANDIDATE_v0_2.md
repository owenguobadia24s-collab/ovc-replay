# PD-WP5 Final Canonical Discovery Contract Candidate v0.2

**Status:** `CANDIDATE_ONLY_NOT_AUTHORISED`  
**Packet:** `PD-WP5-CORR1`  
**Return gate:** `PD-G5P`

## Purpose

This candidate closes the Pilot Discovery review-contract defects without changing C2 semantics, trigger thresholds, queue caps, distance weights, clustering logic, source bindings or promotional authority.

## Required review contract

Every future PD-WP5 review input must use `ovc-pd-wp5-pilot-review-input/v2` or a later explicitly approved version. Every decision must include candidate identity, disposition, non-empty notes and exact evidence references.

Disposition-specific requirements:

- `WORKFLOW_ACCEPTED`: acceptance basis and deterministic acceptance criteria.
- `FLAG_WORKFLOW_DEFECT`: `PD-WF-*` code, affected component, actual and expected behaviour, reproduction steps and acceptance criteria.
- `FLAG_UI_FRICTION`: non-empty `PD-UI-*` code list, affected Console surface and component, actual and expected behaviour, reproduction steps and acceptance criteria.
- `DEFER_PILOT_OBJECT`: `PD-DEFER-*` code, objective resolution criteria and next lawful review condition.
- `REJECT_PILOT_OBJECT`: `PD-REJECT-*` code, non-semantic structural or workflow basis and evidence references.

Incomplete or unknown structured fields fail closed before signing. Free-text notes never substitute for required fields.

## Evidence preservation

The signed v1 Pilot Discovery artifacts remain immutable and are not migrated, relabelled or rewritten. Corrections are stored as a separate read-only overlay bound to the original receipt and defect-ledger SHA-256 values.

## Canonical identity rule

No pilot candidate, fingerprint, cluster, medoid, assignment, family or evidence identity may be reused. A canonical run must start from a new approved canonical namespace and derive all identities from the final approved contract, source manifest, code commit and run identity.

## Authority boundary

This candidate does not authorise:

- a second pilot or correction replay;
- canonical Discovery processing;
- identity activation;
- candidate, model, family, semantic, archetype or theory promotion;
- active novelty ranking;
- selector, release or R2 mutation;
- Validation consumption;
- probability, risk, exposure, trading, execution or agent write.

## Acceptance conditions for PD-G5P return

1. v2 schemas are valid and fail closed.
2. the five exact pilot findings have deterministic codes and complete structured evidence;
3. Console presentation exposes the required fields and remains read-only;
4. source signed artifacts are byte-identical;
5. corrected projection is deterministic and separate from original evidence;
6. complete repository tests pass;
7. replay necessity is explicitly recommended without execution;
8. identity-reset procedure is frozen as a candidate;
9. no prohibited authority changes.

Activation requires a new explicit operator decision at `PD-G5P`.

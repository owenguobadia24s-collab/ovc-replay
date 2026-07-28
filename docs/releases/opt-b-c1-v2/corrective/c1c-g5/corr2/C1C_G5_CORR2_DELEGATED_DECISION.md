# C1C-G5-CORR2 — Delegated Packet Decision

- Programme: `OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1`
- Packet: `C1C-G5-CORR2`
- Return gate: `C1C-G5-CORRECTIVE-PILOT-REVIEW`
- Baseline: `8be9ded5a3f42e79d423ee06e2f890bc7cbf7d8b`
- Authority source: operator `DEFER`
- Proposed packet decision: **PASS**, subject to required CI
- Decision authority: `DELEGATED_AUTO_EXECUTABLE`

## Bounded result

CORR2 adds only non-activating review-workflow correction:

- disposition-specific structured fields on the read-only Candidate Detail surface;
- exact queue, candidate-detail, fingerprint and source-lineage evidence references;
- a fail-closed local runner for exactly the two deferred pilot objects;
- immutable hash preservation for the four non-deferred structured-v2 decisions;
- signed closure receipt, ledger, inventory and final gate-input generation;
- no PASS recommendation while any object remains deferred.

## Authority

No machine replay, provider access, canonical Discovery processing or append, selector/release/R2 mutation, Validation use, semantic/family/candidate/novelty/model/threshold promotion, probability, risk, exposure, trading, execution or agent-write authority is introduced.

## Remaining operator boundary

After a tested squash merge, the operator must review the two exact deferred objects locally and sign the CORR2 evidence with the registered Ed25519 key. That work returns to `C1C-G5-CORRECTIVE-PILOT-REVIEW`; this implementation decision cannot close that gate.

## Rollback

Revert only CORR2 code, schemas, tests and records through a new non-destructive commit. Preserve all signed external evidence and the immutable corrective machine run.

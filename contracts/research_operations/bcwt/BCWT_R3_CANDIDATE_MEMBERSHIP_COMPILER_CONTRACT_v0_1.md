# BCWT-R3 Candidate Membership Compiler Contract v0.1

Status: repository implementation contract. Authority effect: NONE.

## Frozen owner binding

This contract implements only the operator-frozen `BCWT-ORG-RECONFIGURATION` generation 1 predicate created by `BCWT-R3-G0`. It must not change candidate identity, thresholds, source population, first-valid chronology, ambiguity policy, dependency treatment, consequence horizons or any other semantic surface.

## Input population

The input is exactly the 5,238 lawful adjacent `OPGS-R3-REF-0.1` transition accounts from the consumed FXCM GBPUSD 15M C0B stream, partitioned into seven uninterrupted source segments. Every normalized row must preserve its exact population-unit identity, source reference, segment, adjacent start/end sequence IDs, start/end FVT and the D10/D12/D14/D15/D16/D17 evidence needed by the frozen predicate.

Cross-segment rows, non-adjacent rows, non-increasing FVTs, duplicate population-unit IDs, incomplete denominators and outcome-bearing inputs fail closed. No row may be silently dropped or coerced into a binary class.

## Frozen classification

`MATCH` requires D17 load-bearing fields evaluable and at least one of: D10 local-frame relocation OBSERVED; D14 internal reorganisation OBSERVED; evaluable D16 local-vs-mesoscopic relation changed between before and after.

`NON_MATCH` requires D17 load-bearing fields evaluable, D12 continuation/persistence OBSERVED, D10 and D14 not OBSERVED, D16 evaluable and unchanged, and D15 confirming the same uninterrupted segment.

If the load-bearing D17 fields are not evaluable, emit `NOT_EVALUABLE`. If neither exact binary rule is satisfied, retain `AMBIGUOUS` unless an upstream typed population/source failure requires a stricter non-binary state. This implementation does not invent numeric graduality, abruptness, displacement or movement thresholds.

## Outcome-blind firewall

Candidate compilation must not read future consequence rows, post-anchor price outcomes, MOC predictive readouts, SFF probabilities, C2E episode IDs, C2P persistent identity, Validation results, trade/position information or any later scientific outcome. Encountering outcome-bearing fields fails closed.

## Completeness and determinism

The canonical membership ledger contains exactly 5,238 unique entries, one per frozen opportunity. `CandidateOccurrence` rows are a derived positive set containing only `MATCH` entries and do not replace the complete denominator ledger. Replay over identical canonical source rows must reproduce the same source-row digest, membership states, reason codes, occurrence set and ledger digest.

## Authority boundary

This packet grants no CandidateEvaluationAdmission/ADMIT_C, no consequence access or execution, no OPT-C/OPT-D, no ACTIVE_* state, and no probability/risk/exposure/trading/execution authority. Scientific consequence execution remains denied until an explicit `BCWT-R3-G1` operator PASS.

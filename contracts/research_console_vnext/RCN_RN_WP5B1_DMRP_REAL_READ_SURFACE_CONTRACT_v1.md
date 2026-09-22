# RCN-RN-WP5B1 DMRP Real Research Operations Read Surface Contract v1

## Authority basis

Operator PASS at `RCN-RN-G5-FIRST-NEW-SOURCE[DMRP]` admits DMRP owner records as the first new real Research Console source for this packet only. The grant is source-scoped, GET/read-only and non-transitive.

## Required behavior

- DMRP remains authoritative for Path 1 / Path 2 semantics and `ResearchCandidateGeneration` identity.
- Research Console validates exact owner records and presents them without construction, repair, merge, ranking, promotion or semantic synthesis.
- The real route is `GET /api/v1/research/dmrp/snapshot`; fixture mode remains available only when the process itself is in fixture mode.
- Real mode has `fixture_fallback=PROHIBITED`.
- Missing candidate, Path-2, correspondence, exposure or negative-evidence objects are displayed as explicit unbound/unknown states. Their absence is never converted into a scientific negative.
- In particular, missing exposure evidence never establishes independence.
- Validation stays `LOCKED_UNCONSUMED` and transport mutation methods stay denied.
- DMRP source admission does not admit RCCR, PRSC/EC1, OPT-C, OPT-D, C2P, C2.5 or C3.

## Bound owner records

The real-source binding registry pins the exact DMRP current-state pointer, the exact completed `DMRPI-GREAL-EC1` owner state, and the DMRP object-type registry by repository path, schema and Git blob SHA. Any mismatch fails closed.

## Non-grants

No candidate/theory/semantic promotion, candidate freeze, Development/Validation consumption, publication, probability, risk, exposure, trading, execution, governance write or agent-write authority is created.

## Rollback

Disable the DMRP real-source binding and return WP5B1 to fixture/shadow-only presentation while preserving owner records, source-gate evidence, architecture reconciliation and Git history.

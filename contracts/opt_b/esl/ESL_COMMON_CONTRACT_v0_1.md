# OPT-B ESL Common Contract v0.1

Programme: `OVC-OPTB-ESL-CONFORMANCE-v0.1`  
Packet: `ESLI-WP1`  
Authority: inactive deterministic conformance only.

## Constitutional rules

1. Every canonical fact has one owner. StructuralOccurrence may reference upstream facts but may not redefine them.
2. StructuralOccurrence is an immutable cutoff-bounded composition under one exact OccurrencePack. It is not a C2P object, C2E episode, family or semantic term.
3. EvidenceFrontier independently binds evaluation cutoff, exact required/optional/missing references, dependency roles, source-generation IDs, latest required first-valid time and comparability domain.
4. Required identity-defining inputs must be AVAILABLE and their FVT must not exceed output FVT or evaluation cutoff. No hindsight/backdating is permitted.
5. OPTIONAL absence degrades only declared dependent fields. Missing/NOT_EVALUABLE/NOT_COMPARABLE never become zero-equivalent values.
6. FORBIDDEN dependencies fail closed. Reverse edges from SRI/SOI/CEI/C2.5/C3/Research Operations into StructuralOccurrence are prohibited.
7. Comparability is explicit. Identity-defining dependencies with incompatible domains fail closed unless their role is DISPLAY_ONLY or PROVENANCE_ONLY.
8. Generation membership is exact and append-only. Correspondence across generations never rewrites identity.
9. Base ESL remains lawful when C2P, C2E, family, organisation or constraint evidence is absent unless an exact pack declares a dependency REQUIRED.
10. All records emitted by this packet remain `INACTIVE_CONFORMANCE_ONLY`; no selector, scientific, semantic, Validation, publication or exposure authority is created.

## Frozen vocabularies

DependencyRole: `REQUIRED`, `OPTIONAL`, `CONDITIONAL_REQUIRED`, `STRATIFIER`, `FILTER`, `DISPLAY_ONLY`, `PROVENANCE_ONLY`, `FORBIDDEN`.

EvidenceState: `AVAILABLE`, `MISSING`, `NOT_EVALUABLE`, `NOT_COMPARABLE`, `CENSORED`, `AMBIGUOUS`, `CONFLICT`, `QUARANTINED`, `UNRESOLVED`.

ExecutionProfile: `BASE_STRUCTURAL`, `ORGANISATION_ENRICHED`, `CONSTRAINT_ENRICHED`, `FULL_RESEARCH`.

Bootstrap structural dimensions: `LOCATION`, `MOTION`, `ORGANISATION`, `INTERACTION`.

## Validation boundary

`src/ovc/opt_b/esl/validators.py` is the WP1 mechanical guard. It validates owner direction, dependency role/state, exact UTC-Z chronology, FVT monotonicity, generation sets, frontier agreement, comparability and facet missingness. Canonical byte serialization and SHA-256 identity are deliberately deferred to ESLI-WP2.

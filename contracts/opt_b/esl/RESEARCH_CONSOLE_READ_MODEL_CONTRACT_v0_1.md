# ESLI-WP12 Research Console / Read-Model Projection Contract v0.1

Status: inactive deterministic conformance only. Authority effect: NONE.

`ESLReadModel` is a GET-only, source-bound projection over already-materialised ESL and owner records. It may expose occurrence, EvidenceFrontier/evidence states, SRI, OrganisationEvidence, ConstraintEvidence, StructuralTerm qualification, C3 AST/render, authority and lineage information. It MUST preserve owner values, typed null/absence/unresolved states and source lineage exactly.

The projection MUST NOT calculate scientific facts, candidate strength, rankings, probability, forecasts, outcomes, risk, exposure or trade direction. The frontend is a presentation consumer only; scientific computation remains in owning backend/research layers.

Projection creation cannot grant authority. `authority_effect` is always `NONE`; any source authority/maturity shown in the read model is a copied projection of an exact repository record. Unknown projection surfaces fail closed.

`read_model_id` is deterministic over the complete meaning-bearing read-only payload. Source ordering and lineage ordering are canonicalised; source content is otherwise copied without reinterpretation. A fidelity assertion must detect any changed value, omission-to-value conversion, fabricated default, or authority uplift.

# ESLI-WP12 Read-Only ESL Read-Model Contract v0.1

Status: inactive deterministic read-only projection. Authority effect: NONE.

The ESL read model projects already-established backend/source objects only. Every section exposes the exact source owner, source generation, evaluation cutoff, first-valid time, evidence state, denominator when applicable, authority state and lineage references. The projection is replaceable and cannot become the sole source of scientific truth.

Scientific calculation is forbidden in the frontend/read-model layer. No candidate-strength score, information score, profile winner, probability, expected return, risk, exposure, trade direction or execution instruction may be materialised by this projection. Denominators are copied from source evidence and are never inferred from ratios.

The projection exposes no mutation routes and is valid only under an existing read-only Console authority (`READ_ONLY`, `FIXTURE_ONLY_LOCAL_READ_ONLY` or `GET_ONLY`). Any write-capable authority request fails closed.

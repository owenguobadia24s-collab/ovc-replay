# RC-G3 operator decision

Decision: `PASS_RO2_READ_ONLY_ADAPTER_CONSUMPTION`

The Research Console v0.3 may consume the accepted RO2-G3 presentation adapters for bounded local read-only Research workspace presentation.

Accepted consumption includes workspace, quality, lineage, admissible-cutoff replay and release/workspace comparison projections. Discovery and Development may be presented read-only. Validation remains metadata-only with `LOCKED_UNCONSUMED`; Validation content is denied before presentation.

The Console entry point now loads only an allowlisted RO2 projection schema, rejects unknown roles and write-capable payloads, and fails missing or malformed state to `NOT_EVALUATED`.

This decision does not authorise research-record writes, repository mutation, selector mutation, threshold mutation, release activation, market classification, probability, exposure, trading, execution, agents or remote deployment.

Authority delta: `LOCAL_READ_ONLY_RESEARCH_SURFACE_ONLY`.

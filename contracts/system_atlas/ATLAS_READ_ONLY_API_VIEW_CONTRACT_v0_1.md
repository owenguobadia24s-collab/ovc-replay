# Atlas Read-Only API and View Contract v0.1

Programme: `OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1`

Gate: `ATLAS-G7`

The Atlas API is generation-bound and read-only. `GET` retrieves metadata; `POST` is permitted only for deterministic query and view-projection semantics. `PUT`, `PATCH`, `DELETE`, and arbitrary `POST` routes are denied. Every success and controlled-error envelope includes graph generation, repository tree, query-policy version, completeness profile, effective security visibility, warnings, and `write_effect=NONE`.

Caller permissions are resolved by trusted server configuration. Request headers or bodies cannot grant visibility. Every query family must have an admitted PASS `QueryEquivalenceReceipt`; a missing or failed receipt denies API conformance for that family. Query execution intersects the server-resolved caller partitions with the source partition enforced by the generation.

View projection is server-side, deterministic, and bounded. It returns only selected visible entity display/state fields and visible relationships whose endpoints are both selected. It never includes source evidence locators. A capacity breach returns a typed empty incomplete projection rather than a truncated sample.

The committed OpenAPI document and generated TypeScript client under `src/ovc/system_atlas/generated` are deterministic outputs of the qualified API surface. They expose no mutation operation, credential-derived visibility, Research Console binding, canonical publication, or activation path.

# MCARB External Artifact and Research Operations Integration v0.1

MCARB reuses Research Operations evidence-envelope principles without inheriting publication or write authority.
Git may contain only compact contracts, schemas, registries, fixtures, decisions, manifests, QA packets and summaries.
Raw provider data, full AL/ET/VS streams, pair/dependence matrices, caches and bulky run artifacts remain external.

Every external reference must contain exactly: `artifact_id`, lowercase SHA-256, byte size, media type and storage class.
Signed URLs, credentials and operator-machine absolute paths are prohibited. A missing external object makes its dependent
evidence `PARTIALLY_AVAILABLE` or `NOT_REPRODUCIBLE`; it is never silently regenerated from a provider.

Market-derived evidence envelopes bind the exact accepted `source_release_id`, `source_record_ids` and `admissible_cutoff`.
Audit events are append-only by stable `event_id`; duplicates are rejected. No envelope changes source or model authority.

R2 publication remains DENIED. Research Operations integration is local/read-only evidence integration only.

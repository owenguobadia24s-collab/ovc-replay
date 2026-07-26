# OVC RO2-WP3 Research Console adapter contract v0.1

Status: `IMPLEMENTED_CANDIDATE_PENDING_RO2_G3`

RO2-WP3 projects accepted RO2-G1 and RO2-G2 read models into the Research Console v0.3 Research workspace without creating a new authority source.

## Supported read-only panels

- workspace and role context;
- data-quality status;
- exact lineage trace;
- admissible-cutoff replay summary;
- release and workspace comparison.

## Required boundaries

- Every projection is deterministic and carries a stable projection identity.
- Discovery and Development may expose accepted read-only content.
- Validation exposes release identity and aggregate metadata only.
- Validation rows, paths, objects, timestamps and observation identities are denied before resolution.
- Prospective replay exposes accepted IDs and only the count of hidden post-cutoff records; hidden IDs are not emitted.
- No adapter writes to Git, R2, releases, selectors, parameters, thresholds, classifications or execution services.
- No market, probability, exposure, trading, execution or autonomous-agent authority is created.
- Source releases, manifests, observations and RO2 read models always outrank console projections.

## Failure states

Adapters fail closed with explicit unavailable or denied states. Missing panels do not create synthetic evidence, and forbidden write-capable or Validation-content payloads are rejected before projection.

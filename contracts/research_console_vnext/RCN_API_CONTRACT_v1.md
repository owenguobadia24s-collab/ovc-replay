# Research Console vNext API Contract v1

The v1 transport is local-loopback, read-only and fixture-first through RCN-G3V. It projects application-service data and never owns OVC scientific semantics or authority.

## Invariants

- Every public route is `GET`; POST/PUT/PATCH/DELETE are explicitly denied with `MUTATION_METHOD_DENIED`.
- Runtime launch binds `127.0.0.1` only. Network scope is `LOOPBACK_ONLY`.
- Every successful response carries `schema_id`, exact `source_identity`, capability metadata and the persistent `SYNTHETIC_FIXTURE / NON_EVIDENTIARY / authority_effect=NONE` fixture banner.
- `AVAILABLE`, `AUTHORISED` and `ACTIVE` are independent values. `CapabilityDependencyStatus` also exposes implementation state, source materialization, source compatibility, blockers, typed dependencies and last verified commit.
- Missing current-generation sources fail closed with typed reason codes; historical C2E/SRFD fallback is prohibited.
- Validation requests are rejected before fixture object resolution.
- Query ordering is backend-owned. Cursor pagination and market range bounds are deterministic.
- Cache keys are canonical over semantic query inputs, independent of filesystem path or worker. Cache execution is disabled by default in WP2.
- Browser code may navigate, filter, request and render; it may not calculate scientific classifications, family scores, confidence, authority or promotion states.
- All WP2 routes remain fixture-only/local-disabled. Real source-backed route exposure is reserved to later operator gates.

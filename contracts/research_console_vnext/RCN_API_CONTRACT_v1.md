# Research Console vNext API Contract v1

The v1 transport is local-loopback, read-only and fixture-first through RCN-G3V. It projects application-service data and never owns OVC scientific semantics or authority.

## Invariants
- HTTP routes under `/api/v1` are GET-only in WP2; no POST/PUT/PATCH/DELETE route exists.
- Every fixture response contains a persistent `fixture_banner` with `SYNTHETIC_FIXTURE`, `NON_EVIDENTIARY`, `FIXTURE_ONLY` and `authority_effect=NONE`.
- AVAILABLE, AUTHORISED and ACTIVE are separate fields where present; the API never infers one from another.
- Missing current-generation sources fail closed with typed reason codes; historical C2E/SRFD fallback is prohibited.
- Validation content and repository mutation are denied.
- Stable ordering is backend-owned. Cursor pagination is deterministic and bounded.
- Browser code may navigate, filter, request and render; it may not calculate scientific classifications, family scores, confidence, authority or promotion states.
- Runtime launch binds `127.0.0.1` only.

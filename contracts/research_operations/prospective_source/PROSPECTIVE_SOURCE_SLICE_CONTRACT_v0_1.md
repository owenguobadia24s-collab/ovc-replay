# Prospective Source Slice Contract v0.1

A `ProspectiveSourceSlice` is an immutable, local-only description of fresh provider source objects used by Research Operations. It is not an OPT-A release and has no selector or R2 eligibility.

## Required identity

- `slice_id`
- `instrument=GBPUSD`
- `provider=DUKASCOPY`
- half-open `source_window_start_utc` / `source_window_end_utc`
- exact M1 BID, M1 ASK, H1 BID and H1 ASK source-object descriptors
- canonical manifest SHA-256
- `frozen=true`
- explicit coverage state

## Rules

1. Source bytes remain outside Git; Git may contain only compact manifests, hashes, fixtures and QA receipts.
2. No gap is filled, interpolated or inferred.
3. A 15M bucket requires exactly 15 complete aligned M1 parents; a 2H bucket requires exactly 120.
4. Native H1 is a reconciliation control and cannot repair M1.
5. A frozen slice is never edited. New data or provider replacement creates a successor identity.
6. Machine path, runtime and host name are excluded from logical identity.
7. Release, selector, R2, Validation and exposure eligibility are always `NONE` or `DENIED`.

# CBS Source and Input Projection Contract v0.1

CBS reads the exact current owner-published C2 source surface and exact current C2E reference pack through content-addressed adapters. Owner source facts must not be reconstructed from raw/downstream data, private introspection, narrative summaries or comparator output. Missing/conflicting owner identity is `SOURCE_BINDING_INCOMPLETE` or `C2E_REFERENCE_PACK_UNRESOLVED` and blocks the affected surface.

Every comparator has a frozen `ComparatorInputProjectionManifest` declaring public source fields, transforms, scaling, representation, missingness, chronology and first-valid-time handling. Hidden comparator-specific source fields are forbidden. Projection changes after result exposure create a successor generation.

Every comparator also has a `ComparatorSupportManifest` declaring warmup, lookback, lookahead, edges, gaps, censoring, abstention and evaluability. Unequal support requires both matched-support and full-population analyses. A denominator formed from detected positives is `ASCERTAINMENT_FAIL`; method failure is never silently converted to information absence.

The `BoundaryEvaluationUniverse` is formed before comparator detections and contains all eligible temporal opportunities/cutoffs, including estimated, no-estimate, unmatched, ambiguous, censored and not-evaluable states. Count conservation is mandatory. C2_RAW_TYPED primary-representation coverage is classified only as `DIRECT_OWNER_PUBLIC`, `LAWFULLY_DERIVED`, `ABSENT_REQUIRED` or `FORBIDDEN`.

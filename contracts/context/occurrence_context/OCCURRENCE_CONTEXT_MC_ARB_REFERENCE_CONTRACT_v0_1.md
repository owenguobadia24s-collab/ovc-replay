# OccurrenceContext Auxiliary Reference Contract v0.1

Auxiliary MCARB integration is reference-only and inactive by default. Supported reference categories are `ACTIVITY_LIQUIDITY`, `INTRINSIC_EVENT_TIME`, `VOLATILITY_STATE`, and `PROVIDER_SOURCE_CHARACTERISTIC`.

A reference binds exact record ID, schema ID, logical hash, domain, pack/version, source release, first-valid time, qualification record/status, context-admission ID, availability state, and an optional compact allowlisted descriptor. Arbitrary vectors, embeddings, normalized feature maps and mutable payload copies are prohibited.

Non-fixture population requires an explicit auxiliary-admission registry entry naming the exact record class/version and allowed context role. A benchmark result or completed MCARB programme never self-activates a field. The initial registry is `NO_SCIENTIFIC_ADMISSIONS`, so no MCARB record class is activated by this base implementation.

Any later use beyond inert contextual reference requires its own separately governed authority.
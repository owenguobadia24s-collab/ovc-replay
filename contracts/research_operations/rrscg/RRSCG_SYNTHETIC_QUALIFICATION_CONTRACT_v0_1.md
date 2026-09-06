# RRSCG synthetic qualification contract v0.1

This contract qualifies the inactive repository-native RRSCG core over a
deterministic synthetic, single-clock development-conformance population. The
only clocks are local `15M` and parent `2H_A_L`; the source generation and seed
are frozen in the qualification fixture manifest.

Cases are ordered by exact source sequence and case identity. Fresh, chunked,
reordered and checkpoint-split executions must yield the same canonical record
sequence and SHA-256. Duplicate case or sequence identities and tampered parent
state fail closed. Denominators reconcile at R2, D9 and D10; the only permitted
D10 change remains the frozen reducer-layer edge.

The bounded capacity case contains 20,000 synthetic observations and must
complete in under 60 seconds with less than 512 MiB resident-memory growth in
the test process. These are conformance limits, not production service levels.

This contract grants no real-source, provider, Validation, capability
activation, scientific promotion, selector, publication, probability, risk,
exposure, trading or execution authority.

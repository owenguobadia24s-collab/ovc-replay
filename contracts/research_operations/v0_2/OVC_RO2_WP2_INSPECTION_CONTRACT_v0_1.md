# OVC RO2-WP2 inspection contract v0.1

Status: `IMPLEMENTED_CANDIDATE_PENDING_RO2_G2`

RO2-WP2 provides four bounded, replaceable, local read-only projections:

1. deterministic data-quality projection;
2. exact object-to-parent, manifest and release lineage inspection;
3. admissible-cutoff replay for Discovery and Development;
4. deterministic release/workspace comparison.

## Authority boundary

- Validation consumption remains `LOCKED_UNCONSUMED`.
- Validation replay is denied before any path, object or row resolution.
- Outputs are derived inspection records and never outrank source releases, manifests or observations.
- No Git, R2, selector, release, threshold, classification or execution writes are permitted.
- No probability, exposure, trading or autonomous-agent authority is created.

## Determinism

All lists are canonically sorted. Comparison identities use canonical JSON SHA-256. Repeated runs over equivalent logical inputs must produce identical outputs.

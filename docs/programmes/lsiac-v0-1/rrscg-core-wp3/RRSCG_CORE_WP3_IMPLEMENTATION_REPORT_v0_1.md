# RRSCG Core WP3 — D10 reducer conformance implementation

WP3 resumed from the preserved availability blocker after the exact D10 freeze
candidate was rematerialised from the operator-provided Google Drive mount and
matched the court-record SHA-256. The corroborating exact release bundle and
release binding also matched, including byte equality between the standalone
candidate and the nested release copy.

The repository transport is deliberately narrower than the complete external
D10 reference package. `ovc.research_operations.rrscg.d10` consumes a verified
D9 state and emits only a reducer result. The exact D9 state, geometry, motion,
trajectory and parent-R2 mechanics remain in their existing modules and are not
superseded.

The only admitted reducer edge is:

`MINIMAL_CONSTRAINT -> C_LAST_FAMILY_CONSENSUS`

with D10 selected Q a subset of the D9 selected Q. Full, coarse, minimal where
unaffected, and abstention behaviour remain identical. Parent-control mismatch,
view-set drift and out-of-envelope output fail closed.

Source verification passed 64/64 internal hashes, eight semantic checks, 1,024
exhaustive reducer cases, 1,027 parent-R2 equivalence cases, release binding and
the post-seal full-chain check. The repository reducer independently matched the
bound reference over the same 1,024 boolean cases.

Authority remains unchanged: the capability is inactive, the claim cap is
`DESCRIPTIVE_DEVELOPMENT_ONLY`, Validation is locked-unconsumed, and publication,
probability, risk, exposure, E-H, trading and execution remain none.

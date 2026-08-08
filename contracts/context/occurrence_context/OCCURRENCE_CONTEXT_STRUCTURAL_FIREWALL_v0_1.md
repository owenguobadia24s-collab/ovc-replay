# OccurrenceContext Structural Firewall v0.1

The following are blocking invariants.

1. Building, rebuilding or superseding context changes no C2 ID, C2 logical hash, C2E genesis/snapshot/phase/boundary/membership ID or upstream bytes.
2. `occurrence_key` is structural-anchor-only. Session, date, era, clock position, elapsed duration/count, market condition, MCARB, family, semantic and outcome values are excluded.
3. Context enrichment is append-only. An existing context record is never mutated.
4. Future C2P base identity MUST be context-independent; this contract grants no C2P implementation authority.
5. SRI/FDI/family distance receives context only through a separately versioned representation pack with explicit field-level admission. Base v0.1 has no such admission.
6. C2.5/C3 must use typed declared field dependencies; no implicit context inheritance.
7. Outcomes, forward returns, MFE/MAE, probability, edge, risk, exposure, trade or execution state, and Validation occurrence evidence are forbidden context dependencies under current authority.
8. Missing upstream evidence is never repaired or synthesized by context.

Violation disposition is `BLOCK` or `QUARANTINED`, never warning-only.
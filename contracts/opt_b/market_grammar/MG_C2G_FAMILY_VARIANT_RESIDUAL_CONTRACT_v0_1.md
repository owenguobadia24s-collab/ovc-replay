# MG C2G FamilyVariant and Residual Contract v0.1

**Contract ID:** `MG-C2G-FAMILY-VARIANT-RESIDUAL-0.1`  
**Programme:** `OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1`  
**Packet:** `MG-WP4`  
**Authority:** inactive, noncanonical `SHADOW_EXPERIMENT` only

MG-WP4 consumes an exact MG-WP3 `SensitivityResult` and the same typed structural record population. It never changes a family, sensitivity pack, C2 or C2E record.

For each sensitivity-specific family, variant discovery uses only the parent pack's declared `variant_radius`, structural feature weights and minimum support. The deterministic real variant medoid maximises covered parent-family members, minimises covered distance and then uses lexicographic record identity. A variant is `STABLE_UNDER_PACK_CRITERIA` only when support meets the frozen minimum, every member is within `variant_radius`, the medoid is a real member and dispersion does not exceed that radius. No variant is canonical or promoted.

Every input receives one explanation state: `VARIANT_ASSIGNED`, `VARIANT_AMBIGUOUS`, `FAMILY_RESIDUAL`, `FAMILY_AMBIGUOUS`, `FAMILY_UNASSIGNED` or `NOT_EVALUABLE`. Residuals and unassigned records carry explicit reason codes. A counterexample record is an explanatory negative-evidence object, never a semantic label.

Variant identity includes parent family, pack, exact member identities, real medoid and structural invariant/range summary. Provenance, machine/path labels, future data, outcomes, semantic labels, probability, risk, exposure and execution are forbidden from variant construction.

Acceptance requires real family and variant medoids, deterministic input-order invariance, stable-pack criteria for every emitted variant, an explanation for every input, no silent residual/unassigned member, focused and complete repository tests plus FINAL_HEAD/compatibility/merge-readiness and zero unresolved review threads.

Rollback removes or supersedes the inactive variant/residual implementation while preserving MG-WP3 families, pack registry, fixtures, QA, decisions and negative evidence. It must not rewrite upstream family membership.

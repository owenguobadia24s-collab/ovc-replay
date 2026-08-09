# IROF Current-Layer Adapter Binding Contract v0.1

Status: INACTIVE ADAPTER WIRING. Authority effect: NONE.

## Binding rule

IROF binds current owner implementations; it does not replace them. Each current stage has one exact source-module set and one owner authority. Historical/superseded implementations are not runtime fallbacks.

Current bindings cover OPT-A handoff, C1, revised C2 (`c2_vnext` only), inactive C2E v0.2, OccurrenceContext, SFC SRI/comparison/FDI/FamilyEvidenceStream and Research Operations. MCARB remains an unavailable extension until its separate pack and authority are admitted.

## Adapter modes

- `OPAQUE_OWNER_HANDOFF`: IROF relays owner artifact references and owner scientific hash without inspecting or rewriting payload semantics.
- Current callable invocation may call an existing deterministic owner function directly; the returned object is not normalized or re-authored by IROF.
- C2E/SFC bindings remain synthetic/inactive-only unless the owner programme separately authorizes real execution.
- Research Operations remains read-only evidence integration.

## Scientific preservation

Wrapper equivalence requires exact preservation of owner scientific output. In particular, frozen SRFD v0.4 rule-pack IDs, numerators, denominators, statuses and reason codes remain source-owned and unchanged.

## OccurrenceContext boundary

OccurrenceContext is context/stratification metadata by default. `REPRESENTATION_INPUT` is rejected absent an independently authorized representation-pack role declaration. Whole-envelope structural consumption is not inferred by IROF.

## Profiles

The current profile registry must contain `C1_ONLY`, `C2_ONLY`, `C2_C2E`, `STRUCTURAL_CORE`, `FAMILY_RESEARCH`, `FULL_DESCRIPTIVE` and `FULL_DESCRIPTIVE_WITH_CONTEXT`. Profiles select DAG subgraphs only and may not modify stage semantics or authority.

## Rollback

Unregister the IROF current-layer binding. Owner stages, outputs, selectors and contracts remain unchanged.

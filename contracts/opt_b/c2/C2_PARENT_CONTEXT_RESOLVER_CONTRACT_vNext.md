# C2 Parent-Context Resolver Contract vNext r1

Programme: `OVC-C2-ANATOMY-REDESIGN-v0.2`  
Packet: `C2AR-WP8-IMPLEMENTATION`  
Gate: `C2AR-G8A`  
Operator authority: `CEAR-G8.OPERATOR.PASS.20260805T062900+0100`  
Maturity: `SHADOW_FROZEN_READ_ONLY`

## Purpose

Parent context is a typed bundle of independently identified links. It is not one blended parent field, a recreated local `PARENT_RANGE`, an interpretive label or a hidden winning context.

The bundle keeps these families separate:

1. `FIXED_PARENT_OBSERVATION_LINK` — the latest expected completed `2H_A_L` UTC-0000 slot available at the local observation first-valid time.
2. `PARENT_CLOCK_STRUCTURAL_PROJECTION` — parent-owned measurement, structural, axis and depth objects linked by exact identity and definition hash.
3. `HIGHER_ORDER_LOCAL_CLOCK_PROJECTION` — higher structural depth on the local 15M clock, explicitly not equivalent to the fixed 2H parent.
4. `EPISODE_CONTEXT` — a separate optional event-relative link that remains unavailable without independent C2E or C2.5 authority.

## Fixed-parent chronology

For each local observation, the resolver shall:

1. validate the local identity and first-valid time;
2. calculate the latest expected completed two-hour slot on the registered `2H_A_L` UTC-0000 lattice whose interval end is less than or equal to the local first-valid time;
3. resolve that exact expected slot before applying completeness filters;
4. require exact instrument, side, release, calendar, lattice and source compatibility;
5. require the parent interval end and parent first-valid time not to exceed the local first-valid time;
6. link the parent only when the exact expected slot is uniquely present and `COMPLETE`.

Equality between parent and local first-valid time is allowed. Future input is prohibited.

A missing, incomplete, gapped, conflicted, censored, unresolved-closure or not-first-valid expected slot clears every dependent parent link. The resolver shall not carry an older observed parent forward and shall never populate a fallback parent ID.

## Parent-object projections

Parent objects retain authority in the parent scope. Local processing references their object IDs, parent-observation IDs, definition hashes, first-valid times and source identities. It does not reconstruct them as local levels or containers.

`PARENT_MEASUREMENT`, `PARENT_STRUCTURAL`, `PARENT_AXIS_CONTEXT` and every structural depth are separate projections. Each projection exposes the complete role inventory, eligible IDs, exclusions, ties, nullable selected ID, selection reason, resolver version and a permanently null fallback field.

Selection is permitted only when exactly one object is eligible for the declared role and depth under the exact resolver profile. Zero eligible objects returns `NO_ELIGIBLE_PARENT_OBJECT`. More than one eligible object returns `MULTIPLE_ELIGIBLE_NO_GOVERNED_SELECTION`. Latest, nearest, widest, smallest, best-parent, best-lattice, best-structure and fallback selection are prohibited.

## Refresh and computability

The link bundle is recomputed for each local observation. Parent objects are not recreated or refreshed by the local clock. Link states are `LINKED`, `REFRESHED`, `UNCHANGED`, `CLEARED` or `NOT_COMPUTABLE`; they are context lifecycle facts, not local market transitions.

Computability is independent by component. Parent absence affects only dependent products and cannot collapse the whole bundle into a global degraded state. Reason codes, inventories and exclusions remain visible.

## Age evidence

Raw age evidence includes elapsed duration, eligible local-observation count, parent-slot count, registered closure count, parent-observation age, parent-object age and role-projection age. No universal freshness or staleness threshold is selected. Consumer-specific staleness, denominator and overlap policy remain reserved for CEAR-G9.

## Higher-order local and episode context

Higher-order local-clock objects are inventory links only and carry `parent_equivalence=false`. They cannot substitute for the fixed parent.

Episode candidates remain separately visible but ineligible with `EPISODE_AUTHORITY_UNAVAILABLE`. This contract does not activate C2E, C2.5, events or episodes.

## Authority boundary

All outputs are inactive, noncanonical and `SHADOW_FROZEN_READ_ONLY`. This contract grants no active or canonical parent selection, numeric threshold, semantic event or episode promotion, denominator or overlap policy, rule or theory, provider intake, canonical or R2 publication, Validation consumption, active C2 selector or release change, probability, risk, exposure, trading, execution or agent writes.

## Rollback

Disable or remove shadow consumers and rebuild outputs from their immutable inputs. Preserve the CEAR-G8 operator decision, accepted identities, chronology, no-fallback rule and separation between fixed parent, parent structure, higher-order local structure and episode context. A material policy change requires a new operator-authorised version and `SUPERSEDE` record.

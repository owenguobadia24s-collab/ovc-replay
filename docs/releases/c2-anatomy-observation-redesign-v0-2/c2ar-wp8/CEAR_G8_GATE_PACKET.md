# CEAR-G8 — Parent-Context Resolver Policy Freeze

**Programme:** `OVC-C2-ANATOMY-REDESIGN-v0.2`  
**Plan:** `OVC-C2-ANATOMY-REDESIGN-IMPLEMENTATION / 0.2-REVISED`  
**Packet:** `C2AR-WP8`  
**Baseline main:** `841e91a4dd9f89372aa64fb87721a9eb71f9eb56`  
**Authority:** **OPERATOR REQUIRED**  
**Recommended decision:** **PASS**

## Decision

Approve a versioned parent-context resolver policy for later **inactive, noncanonical, read-only shadow implementation only**.

The central rule is:

> Parent context is a typed bundle of independently identified links. It is not one blended `parent_context` or `PARENT_RANGE` field.

The bundle keeps four things separate:

1. `FIXED_PARENT_OBSERVATION_LINK` — the latest expected completed `2H_A_L` UTC-0000 slot lawfully available to the local observation.
2. `PARENT_CLOCK_STRUCTURAL_PROJECTION` — exact parent-owned measurement, structural, axis and depth objects.
3. `HIGHER_ORDER_LOCAL_CLOCK_PROJECTION` — higher structural depth derived on the local 15M clock, explicitly not equivalent to a fixed 2H parent.
4. `EPISODE_CONTEXT` — an optional event-relative C2E/C2.5 link, unavailable without separate authority.

## Fixed-parent resolution

For each local observation, the resolver must:

1. validate the local identity and first-valid time;
2. compute the latest **expected completed** `2H_A_L` UTC-0000 slot whose interval end is less than or equal to the local first-valid time;
3. resolve that exact scheduled slot before applying completeness filters;
4. require exact instrument, side, release, calendar, lattice, source identity and chronology compatibility;
5. link the complete parent or clear every dependent parent link.

Equal local and parent first-valid timestamps are permitted. A future parent is prohibited.

A missing, incomplete, gapped, conflicted, censored, unresolved-closure or not-first-valid expected slot does **not** cause fallback to an older observed parent. It produces explicit non-computability and clears dependent links.

## Parent-object resolution

Parent objects remain authoritative in their own scope. Local processing links their IDs and definition hashes; it does not recreate them as local levels, containers or a synthetic `PARENT_RANGE`.

Parent measurement, parent structure, parent axes and every structural depth are separate projections. Each projection exposes:

- the complete candidate inventory;
- eligible IDs;
- exclusions and reasons;
- ties;
- nullable selected ID;
- selection reason;
- resolver version;
- a permanently null fallback field.

A projection may select an object only when exactly one object is eligible for the declared role and depth under the exact resolver profile. Zero eligible objects returns `NO_ELIGIBLE_PARENT_OBJECT`. Unresolved multiplicity returns `MULTIPLE_ELIGIBLE_NO_GOVERNED_SELECTION`.

No latest, nearest, widest, smallest, best-parent, best-lattice, best-structure or fallback selection is allowed.

## Refresh, age and computability

The context link is recomputed for each local observation, but a local bar never refreshes or recreates the parent object. Link changes are context lifecycle facts—`LINKED`, `REFRESHED`, `UNCHANGED`, `CLEARED` or `NOT_COMPUTABLE`—not local market transitions.

Age evidence remains multidimensional:

- elapsed duration;
- eligible local-observation count;
- parent-slot count;
- registered closure count;
- parent-observation age;
- parent-object age;
- role-projection age.

CEAR-G8 selects no universal freshness or staleness threshold. Consumer-specific staleness, denominator and overlap policy remain reserved for CEAR-G9.

Parent absence affects only products that depend on the missing component. It must not collapse all axes or all context into one global degraded state.

## Explicit exclusions

This decision does not grant:

- resolver execution before the post-PASS implementation merges;
- active or canonical parent selection;
- hidden parent, lattice, structure or object selection;
- numeric freshness or staleness thresholds;
- semantic event or episode promotion;
- C2E or C2.5 activation;
- consumer denominator or overlap policy;
- rule or theory promotion;
- provider intake;
- canonical or R2 publication;
- Validation consumption;
- active C2 selector or release changes;
- probability, risk, exposure, trading, execution or agent-write authority.

## Evidence and QA

The machine-readable packet is `CEAR_G8_GATE_PACKET.json`. The candidate policy is `registries/opt_b/c2/vnext/C2_PARENT_CONTEXT_RESOLVER_CANDIDATE_v0_1.jsonc`.

Required before decision readiness:

- gate-policy tests;
- complete repository suite;
- `FINAL_HEAD` assurance;
- merge readiness;
- zero unresolved review threads;
- proof that active C2 and all reserved downstream authorities remain unchanged.

No external artifact or market data is required. No R2 write occurs.

## Rollback

Before approval, close this PR unmerged and retain WP7 main. After approval, preserve the immutable decision and supersede it only through a new versioned operator record. A later shadow implementation can be rolled back by disabling its consumers; active C2 requires no rollback because it remains unchanged.

## Exact work after PASS

Record and merge the immutable CEAR-G8 decision; implement the resolver only as inactive, noncanonical shadow machinery; run complete assurance; auto-ratify and squash-merge `C2AR-G8A` only when all acceptance conditions pass; seal the receipt; then prepare CEAR-G9 and stop.

## Operator command

`OVC APPROVE CEAR-G8 PASS`

# C2 Level, Swing Graph, Lifecycle and Selector Contract vNext r1

Programme: `OVC-C2-ANATOMY-REDESIGN-v0.2`  
Packet: `C2AR-WP3`  
Gate: `CEAR-G3`  
Normative maturity at gate: `NORMATIVE_BOUNDARY`  
Candidate, graph-adapter and selector implementation: `SHADOW_EXPERIMENT`

## Purpose

A level is immutable first-valid structural evidence, not any price that happens to be extreme. Candidate evidence, level definition, lifecycle, complete inventory, graph construction and consumer projection are separate products. No numeric pivot policy or current selector is activated.

## Accepted Part 3 decisions

| ID | Frozen rule |
|---|---|
| P3-D1 | A candidate extreme is not a level. |
| P3-D2 | A level enters relations only at causal `first_valid_time`, never at anchor time. |
| P3-D3 | Families share one `C2.REFERENCE_LEVEL` envelope but retain separate construction and lifecycle rules. Equal price never implies equal identity. |
| P3-D4 | Range types are `TRAILING_RANGE_HIGH` and `TRAILING_RANGE_LOW`, explicitly diagnostic window references. |
| P3-D5 | Swing types are `CONFIRMED_SWING_HIGH` and `CONFIRMED_SWING_LOW`, explicitly requiring registered causal confirmation. |
| P3-D6 | `TRAILING_RANGE_MIDPOINT` is exact parent-bound derived evidence with no independent confirmation or lifecycle. |
| P3-D7 | Definitions are immutable; lifecycle changes are append-only events. |
| P3-D8 | Crossing, contact and later interaction never delete, rewrite or invalidate a level definition. |
| P3-D9 | New swings update projections but never delete earlier swings. |
| P3-D10 | Full inventory and current pointers are separate products. |
| P3-D11 | Parent levels are linked by identity and lineage, not recreated as local authority. |
| P3-D12 | Staleness and retirement are family- and consumer-specific; no universal expiry exists. |
| P3-D13 | Tied candidates are explicit ambiguity, never silent neutrality. |
| P3-D14 | Container-boundary identities and lifecycle remain governed by Part 4; Level may carry pointer roles only. |
| P3-D15 | Canonical numeric horizons and pivot parameters remain deferred to replay, QA and a later operator gate. |

## Accepted multiscale refinements

- **P3-R1:** every swing declares observation clock and structural depth.
- **P3-R2:** `2-left/2-right` is a non-canonical 15M and 2H research baseline only.
- **P3-R3:** S1/S2 are generated through explicit pivot-of-pivots lineage.
- **P3-R4:** trailing ranges remain diagnostic measurements and are not swing envelopes.
- **P3-R5:** persist swing nodes, legs, hierarchy edges and envelope candidates.
- **P3-R6:** current pointers are derived and never delete history.
- **P3-R7:** consumers use named, versioned, transparent selectors.
- **P3-R8:** raw prominence, duration, efficiency, age and interaction counts precede labels.
- **P3-R9:** fixed 2H context, 2H swings and higher-order 15M swings remain distinct objects.

## Working dispositions

- **P3-Q1:** plateau evidence emits one `AMBIGUOUS_PLATEAU` candidate; no confirmed level exists until a separately approved compound-anchor rule passes.
- **P3-Q2:** a trailing-range lineage persists while the same anchor persists, but each exact trailing population creates a new snapshot version.
- **P3-Q3:** preserve the complete graph; consumer-specific age, newer-swing count, distance and discontinuity policies remain deferred.
- **P3-Q4:** midpoint remains in `DERIVED_REFERENCE`; Part 4 owns the parent container/range object.
- **P3-Q5:** same-price definitions remain independent; any future cluster is additive and cannot merge definitions in place.

## Families

`WINDOW_BOUNDARY`, `CONFIRMED_PIVOT`, `DERIVED_REFERENCE`, `CONTEXT_REFERENCE`, and `CONTAINER_BOUNDARY_REFERENCE` share the common envelope. Optional exogenous-convention levels remain registered but inactive and are not constructed by WP3.

## Candidate chronology

Every possible anchor is represented as `UNIQUE_CONFIRMED`, `AMBIGUOUS_PLATEAU`, `REJECTED_NOT_EXTREME`, or `CENSORED_CONFIRMATION`. Confirmation requires all left/right members to be eligible and inside one continuity segment. The level's first-valid time is the final confirming member's first-valid time. Censored and ambiguous candidates cannot become levels.

## Identity and immutability

Level identity includes family, type, value, first-valid time, instrument, side, clock, structural depth, origin, source IDs, parent IDs and source release. A side, clock, release, horizon, depth, anchor or origin change creates a new identity. Lifecycle records preserve the definition hash.

## Graph

The complete graph contains ordered swing nodes, consecutive legs and explicit hierarchy edges. S0 derives from observation pivots. S1/S2 use separately registered pivot-of-pivots policies. Cross-clock equivalence is prohibited. Current pointers are rebuildable selector projections over the complete graph.

## Lifecycle

Allowed append-only events are `DEFINED`, `REFRESHED`, `SUPERSEDED`, `STALE_FOR_CONSUMER`, `RETIRED_FOR_CONSUMER`, and `INVALIDATED_SOURCE`. Staleness and retirement require a consumer ID. Supersession points to a new level but does not erase the old definition.

## Selector transparency

A selector result exposes the named selector/version, complete candidate IDs, eligible IDs, every exclusion and reason, ties, nullable selected ID, null fallback, first-valid as-of time and zero active authority. A tie produces no selected level. A selector may not choose an object merely to make a downstream axis, context or rule evaluable.

## Legacy crosswalk

Historical `RANGE_HIGH`, `RANGE_LOW`, `MIDPOINT`, `SWING_HIGH`, and `SWING_LOW` names remain immutable. Crosswalks map them to vNext families by explicit side/type/value evidence and preserve unmatched or multiple matches.

## SHADOW_EXPERIMENT boundary

Candidate payload fields, graph storage adapters, raw-metric payloads, selector adapter fields and non-canonical parameter surfaces may evolve through WP5.5 under revision IDs. They may not weaken identity, chronology, side separation, complete inventory, append-only lifecycle or no-hidden-selection. Integrated freeze is operator-required at CEAR-G6.

## Authority and rollback

No active level, pivot policy, selector, parameter pack, formula, release, publication, Validation or downstream authority changes. Rebuild candidate/graph/projection artifacts as needed; preserve contracts, fixtures, lifecycle events, crosswalks, QA and decisions. Active C2 remains unchanged.

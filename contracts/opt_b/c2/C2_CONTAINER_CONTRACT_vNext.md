# C2 Container, Pairing, Graph and Role-Projection Contract vNext r1

Programme: `OVC-C2-ANATOMY-REDESIGN-v0.2`  
Packet: `C2AR-WP4`  
Gate: `CEAR-G4`  
Normative maturity at gate: `NORMATIVE_BOUNDARY`  
Candidate pairing, graph adapters and projection implementation: `SHADOW_EXPERIMENT`

## Purpose

A container is an immutable, causally first-valid price interval produced from two compatible boundary identities. It records measurement or structural geometry only. It does not create market meaning, episodes, events or a hidden winning context.

## Accepted Part 4 decisions

| ID | Frozen rule |
|---|---|
| P4-D1 | A container requires two compatible, first-valid boundary identities. |
| P4-D2 | One valid boundary is explicit partial evidence and cannot create a container definition. |
| P4-D3 | Measurement containers and structural containers are separate families with separate construction evidence. |
| P4-D4 | `LOCAL` and `PARENT` are explicit projection roles, not container families or authority shortcuts. |
| P4-D5 | Legacy `LOCAL_RANGE` becomes `TRAILING_RANGE_SNAPSHOT`, a diagnostic measurement container bound to one exact causal population. |
| P4-D6 | Parent containers are linked by identity and definition hash; they are not recreated as local authority. |
| P4-D7 | `SWING_ENVELOPE` requires an explicit registered pairing-evidence record over two confirmed opposite-polarity swing boundaries. |
| P4-D8 | Independently selecting the latest high and latest low is prohibited; no implicit pairing exists. |
| P4-D9 | Multiple structural depths and clocks coexist through distinct identities; no automatic equivalence is allowed. |
| P4-D10 | Complete container inventory and current role projections are separate products. |
| P4-D11 | Container definitions are immutable and lifecycle changes are append-only. |
| P4-D12 | Price crossing, entry, exit or later interaction never deletes or rewrites container existence. |
| P4-D13 | Nesting, containment and overlap are explicit graph relations, not a width-derived hierarchy. |
| P4-D14 | Lower value, upper value, width and centre are explicit raw geometry. |
| P4-D15 | Centre is deterministic derived geometry, not a third boundary and not independently confirmed. |
| P4-D16 | Zero-width pairs are rejected and cannot become active containers. |
| P4-D17 | Hidden nearest, widest, smallest, latest, best or fallback container selection is prohibited. |
| P4-D18 | Pairing rules, structural-depth construction and projection rules remain non-canonical replay candidates until a later operator gate. |

## Accepted working dispositions

- **P4-Q1:** shadow-test three separately identified pairing candidates; none is canonical or active at CEAR-G4.
- **P4-Q2:** structural depth above S0 remains a redesign candidate with explicit pivot-of-pivots lineage.
- **P4-Q3:** local projection policy remains an inactive named candidate; complete candidate and exclusion evidence is mandatory.
- **P4-Q4:** expose parent measurement and parent structural context separately rather than collapsing them.
- **P4-Q5:** retirement/staleness bounds remain consumer-specific and deferred; complete history is retained.
- **P4-Q6:** partial overlap is valid raw geometry and must remain visible for Part 5 relation construction.

## Families and evidence

`TRAILING_RANGE_SNAPSHOT` is a measurement container created from compatible `TRAILING_RANGE_LOW` and `TRAILING_RANGE_HIGH` levels sharing exact horizon, population, clock, side, release and first-valid basis.

`SWING_ENVELOPE` is a structural container created only from a confirmed swing low and confirmed swing high under an explicit pairing-policy identity. The pairing evidence is preserved even when partial, incompatible, ambiguous, censored or zero-width.

## Identity and chronology

Container identity includes family, kind, boundary IDs, pairing-evidence ID, first-valid time, horizon, structural depth and origin. First-valid time cannot precede either boundary or the pairing evidence. Clock, side, release, depth, pairing policy, boundary or horizon changes create a new identity.

## Geometry and graph

Every definition exposes lower, upper, positive width and deterministic centre. Graph edges are `CONTAINS`, `WITHIN`, `OVERLAPS`, `DISJOINT` or `EQUAL_BOUNDS` using raw intervals. A partial overlap remains an ordinary graph fact. Width does not determine parentage.

## Lifecycle

Allowed append-only events are `DEFINED`, `REFRESHED`, `SUPERSEDED`, `STALE_FOR_CONSUMER`, `RETIRED_FOR_CONSUMER`, `CENSORED` and `INVALIDATED_SOURCE`. Staleness and retirement require a consumer identity. Definitions and earlier events remain permanently addressable.

## Role projections

The four roles are `LOCAL_MEASUREMENT`, `LOCAL_STRUCTURAL`, `PARENT_MEASUREMENT` and `PARENT_STRUCTURAL`. A named projection result exposes every candidate, eligible ID, exclusion, tie, nullable selected ID, null fallback, rule version and inactive authority. A tie or no-match produces no selected container.

## Parent links

A parent-context link contains the authoritative parent container ID, definition hash, first-valid time, local scope, role and as-of time. It explicitly records that no local container was recreated.

## Legacy crosswalk

`LOCAL_RANGE`, `RANGE_CONTAINER`, `SWING_ENVELOPE` and `PARENT_RANGE` remain historical names. Crosswalks preserve unmatched and multiple matches. `PARENT_RANGE` requires a link rather than a local definition.

## SHADOW_EXPERIMENT boundary

Candidate pairing payloads, graph storage adapters, projection adapter fields, raw metrics and parameter surfaces may evolve through WP5.5. They may not weaken two-boundary construction, identity, first-valid chronology, immutable lifecycle, complete inventory, explicit overlap or no-hidden-selection. Integrated freeze remains operator-required at CEAR-G6.

## Authority and rollback

No active container, pairing rule, projection, selector, formula, threshold, release, publication, Validation or downstream authority changes. Rebuild pairing, graph and projection artifacts as needed; preserve contracts, definitions, lifecycle events, fixtures, crosswalks, QA and decisions. Active C2 remains unchanged.

# OVC System Graph Contract v0.1

Programme: `OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1`

Gate: `ATLAS-G1`

## Canonical Object Families

`OVCSystemGraph` is a typed, evidence-bound, temporally versioned property graph composed of `Entity`, `Relationship`, `Assertion`, `EvidenceReference`, `Conflict`, `Scope`, and `AtlasGraphGeneration` objects.

Every logical object has a typed ID. Display names, repository paths, aliases, screen placement, ordering, process identity, host identity, and runtime measurements do not define logical identity. A possible identity match never merges entities automatically.

Every entity carries separate lifecycle, implementation, availability, assurance, authority, activation, canonicality, currentness, and health planes. A consumer MUST NOT collapse those planes into one status.

## Evidence, Scope, and Negative State

Every relationship and assertion carries at least one `EvidenceReference` and an explicit `Scope`. Scope may constrain programme, generation, instrument, market, side, clock, source release, environment, branch/tree, authority generation, or valid time. Consumers MUST NOT widen omitted or unresolved scope.

Denied, absent, unresolved, ambiguous, conflicting, stale, historical, and design-only results are first-class outcomes. They MUST NOT be hidden or converted into an affirmative relationship.

## Ownership and Authority

Observed connectivity, declared dependency, ownership, authority, and prohibition are distinct relationship families. Graph adjacency, extraction, storage, rendering, or consumption grants no authority or ownership.

All Core graph objects carry `authority_effect=NONE` or the graph-wide equivalent `NONE_READ_ONLY_DERIVED_GRAPH`. High-risk predicates are interpreted only through `ATLAS_PREDICATE_AUTHORITY_REGISTRY_v0_1.json`. Multiple admissible owners for an exactly-one role produce `OWNER_CONFLICT`; lexical order, path, recency, and heuristic confidence are forbidden tie breakers.

## Court Record

`court_record_status=EXACT_GIT_TREE` is permitted only when the generation binds an exact physical commit and tree. Synthetic fixtures use `SYNTHETIC_NOT_COURT_RECORD`. Prospective, dirty-tree, fixture, design-only, and historical graphs MUST remain visibly noncanonical where applicable.

## Projection Boundary

The graph and every caller projection are read-only. This contract creates no Research Console source admission, GRT or Shared Systems authority, scientific semantics, Validation access, write route, activation, promotion, or publication authority.

## Rollback

Derived graphs are disposable. Remove or supersede the generated graph and rebuild from bound evidence; never rewrite upstream court-record sources to make a graph pass.

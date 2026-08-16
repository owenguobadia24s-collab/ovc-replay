# Atlas Query and Equivalence Contract v0.1

Programme: `OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1`

Gate: `ATLAS-G6`

The controlling query semantics are reference-first and deterministic. The admitted families are `SEARCH`, `TRACE`, `DEPENDENCY`, `IMPACT`, `EXPLAIN`, `AUTHORITY`, `OWNERSHIP`, `WHY_BLOCKED`, `HISTORY`, and `DIFF`. Every result binds the graph root, repository tree, query-policy version, completeness profile, visibility projection, warnings, and a canonical result hash.

Search ranks exact typed identity before exact label, exact alias, prefix, and substring matches. Aliases never merge identities. Trace requires an explicit depth no greater than eight, returns one deterministically ranked shortest path per visible entity, reports cycles explicitly, and never defaults to all paths. Dependency distinguishes required, optional, technical-only, historical, and unresolved meaning without converting reachability into governed dependency. Impact is a typed conservative projection and creates no change authority.

Explain returns only visible object and evidence records. Authority and ownership are evidence-bound projections, not fresh authority resolution. Why-blocked returns the minimal visible direct blocking frontier and open conflicts. History and diff bind immutable generation roots and compare only identical visibility projections.

Caller permission and source partition are intersected before query execution. Invisible objects, source locators, relationships, and evidence must not be inferable through counts, paths, explanations, or diff. Capacity failure returns a typed incomplete result and no partial record sample. Partial or degraded coverage is never represented as exhaustive.

An optimized index is disposable and has no semantic standing. Each family requires its own `QueryEquivalenceReceipt` with exact reference/optimized result equality on golden, adversarial, and relevant historical cases. A failed or missing receipt quarantines optimized/API/UI conformance for that family while reference semantics remain controlling.

This contract grants no source access, owner or authority state, publication, operational reliance, activation, or write authority.

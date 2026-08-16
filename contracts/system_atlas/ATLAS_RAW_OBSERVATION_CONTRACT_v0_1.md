# Atlas Raw Observation Contract v0.1

## Status and authority

This contract is a bounded, read-only implementation contract under
`OVC-SYSTEM-ATLAS-CONFORMANCE-IMPLEMENTATION-PLAN-0.1-R1-RATIFIED`.
An Atlas raw observation reports extractor output. It is not a canonical
assertion and has no owner, governance, scientific, validation, write, or
publication authority.

## Exact-tree binding

Each observation MUST bind the extractor ID and version, repository commit and
tree, source path and blob SHA, locator, observation type, raw subject,
predicate and object, scope hints, parse status, evidence class, and normalized
content hash. Exact-tree scans MUST fail closed when tracked worktree changes
could contaminate a scan of `HEAD`. Dirty or otherwise non-court-record scans
may only be represented by a separately declared `PROVISIONAL` mode; this
contract does not admit such a mode to the exact-tree adapter.

## Evidence preservation

The adapter MUST preserve these GRT evidence classes without ranking or
promotion: `SOURCE_EXPLICIT`, `LINEAGE_EXPLICIT`,
`PATH_AND_CONTENT_CORROBORATED`, `TEST_CORROBORATED`,
`IMPORT_CORROBORATED`, `CANDIDATE_RELATION`, `INFERRED`, and `UNRESOLVED`.
Unknown evidence classes fail closed.

GRT `OWNED_BY` and `GOVERNED_BY` edges remain observations, including when
their evidence is source-explicit. Candidate or inferred relationships MUST
NOT become canonical `OWNS` or `GOVERNS` assertions. The adapter emits an empty
`canonical_assertions` collection and records promotion as denied pending a
separate, authorized predicate-resolution packet.

## Determinism

For identical GRT input, exact commit/tree identity, and extractor version, the
logical observation set and its canonical hash MUST be identical regardless of
input collection order. Every edge source MUST resolve to a physical component
in the exact tree. A programme endpoint MUST correspond to a programme declared
by the same GRT read model.

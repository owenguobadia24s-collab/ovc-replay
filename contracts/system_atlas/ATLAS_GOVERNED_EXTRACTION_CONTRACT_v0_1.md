# Atlas Governed Extraction Contract v0.1

## Authority boundary

Governed extractors observe exact source records. They do not resolve identity,
ownership, authority, currentness conflicts, scientific meaning, or canonical
truth. Every output has zero authority effect and an empty canonical assertion
set. WP4 is the earliest packet that may attempt resolution under the predicate
authority registry and its independent algorithmic gate.

## Census and source identity

The extractor MUST consume the physical component census emitted by the GRT
exact-tree adapter. It MUST NOT enumerate the repository independently. Each
selected source is re-read from its bound Git commit and its object ID MUST
equal the GRT component digest. A mismatch fails closed.

The governed source classes are `PROGRAMME_RECORD`, `AUTHORITY_RECORD`,
`CONTRACT`, `SCHEMA`, `REGISTRY`, and `RESEARCH_RECORD`. Source classification
uses only the GRT component type and explicit path class. It does not establish
semantic ownership or authority.

## Observation rules

JSON extractors emit source presence and top-level scalar fields. Markdown and
text extractors emit source presence, ATX headings, and explicit `name: value`
fields. Nested interpretation, prose inference, filename-recency selection, and
high-risk predicate promotion are forbidden. Every observation binds extractor
ID/version, commit/tree, source path/blob SHA, locator, raw subject/predicate/
object, scope hints, parse status, evidence class, and normalized content hash.

Identical exact-tree input and extractor version MUST reproduce the identical
governed observation-set hash independent of GRT component ordering.

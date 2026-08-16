# Atlas Canonical Serialization Contract v0.1

Programme: `OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1`

Gate: `ATLAS-G1`

Atlas logical identities use UTF-8 JSON with lexicographically sorted object keys, no insignificant whitespace, no trailing newline, `allow_nan=false`, and no floating-point values. Integers, booleans, strings, nulls, objects, and arrays are admitted.

The graph object arrays are sorted by their typed identity fields: `entity_id`, `relationship_id`, `assertion_id`, `evidence_id`, and `conflict_id`. Set-like arrays such as aliases and evidence references are deduplicated and sorted. Ordered registry arrays, including precedence and resolver pipelines, retain their declared order.

`graph_logical_hash` is SHA-256 over the canonical graph with the `graph_logical_hash` member omitted. The hash excludes traversal order, formatting, host/process identity, absolute local paths, timestamps, durations, memory observations, and screen placement.

Optimized or incremental implementations have no independent semantic standing. For the same bound source identity and registry versions they MUST reproduce the reference canonical bytes and `graph_logical_hash` before their result can be used.

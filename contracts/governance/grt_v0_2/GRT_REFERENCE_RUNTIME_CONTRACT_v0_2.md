# GRT v0.2 Reference Runtime Contract — WP3A

Status: **INACTIVE / NON-ENFORCING**. Authority effect: **NONE**.

`GRT-REFERENCE-WP3A.v1` consumes an exact caller-pinned Git-tree manifest and deterministically projects L1 `ObservedComponent` records and an L2 `RepositoryArtifact` graph. Physical path/classification evidence is not authority: owner, Genesis binding, current/historical lifecycle and declared relationships are accepted only from explicit bindings. Missing lifecycle defaults to the non-authoritative `PROPOSED_UNADMITTED` class and remains `PARTIAL`.

The scanner never reads branch name, PR number, wall clock, worker order or presentation fields into logical identity. Observed-component identity is exact-tree/path/content scoped. A source-explicit artifact ID is authoritative for projection; absent one, a content/class candidate identity is visibly `CANDIDATE_RELATION` and cannot satisfy owner/Genesis/current-authority rules.

Unknown artifact class, invalid relationship vocabulary, identity collision, malformed tree/hash or missing required input fails closed. `GRT-REFERENCE` is a correctness oracle only; this packet does not admit the Repository Constitution, create DebtFloor generation 0 or activate GRT2-G2.5/G3 enforcement.

B0 replay must reproduce all 569 immutable baseline members and membership SHA-256 exactly. Replay does not itself map B0 members to v0.2 findings or grant grandfathering.

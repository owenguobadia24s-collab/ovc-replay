# Atlas Generation Root and Partition Contract v0.1

Programme: `OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1`

Gate: `ATLAS-G5`

Each immutable Atlas generation is addressed by `root_hash`, the canonical SHA-256 identity of its root-manifest payload before the `root_hash` member is added. The manifest binds the exact graph logical hash, repository commit/tree, completeness profile, source-currentness proof hash, provisional retention state, and every visibility-partition manifest.

The canonical partitions are `ATLAS_PUBLIC_METADATA`, `ATLAS_INTERNAL`, and `ATLAS_RESTRICTED`. Every partition contains deterministic identity-sorted JSONL files for entities, relationships, assertions, evidence references, and conflicts plus a content-addressed partition manifest. An object is placed at the most restrictive partition required by its endpoints, assertions, or evidence. A declared entity partition that is broader than referenced evidence fails closed; restricted metadata is never copied into a broader bundle.

JSONL records use the frozen Atlas canonical JSON encoding followed by one LF. File hashes, record counts, partition hashes, and the root hash are independently verified. Any mismatch quarantines the bundle. Host paths, timestamps, process identity, performance measurements, and builder mode do not enter generation identity.

Reference and incremental builders have no separate semantic authority. Given identical source identity, registries, predecessor identity and proofs, they must emit byte-identical bundles and the same root hash. Divergence quarantines the incremental result and leaves reference semantics controlling.

`ATLAS_CORE` capacity cannot silently sample. A record ceiling violation returns typed `CAPACITY_EXCEEDED`. Optional future profiles may degrade only with a distinct completeness state and must not drop security partitions or high-risk evidence.

This contract grants no source access, owner/authority state, canonical publication, current-pointer switch, operational reliance, or write authority.

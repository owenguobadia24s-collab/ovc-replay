# Atlas GraphStore, Currentness, and Retention Contract v0.1

Programme: `OVC-SYSTEM-ATLAS-CONFORMANCE-v0.1`

Gate: `ATLAS-G5`

`GraphStore` is a disposable SQLite index over one verified immutable generation. It stores canonical object bytes, visibility partition, and generation-aware adjacency. Reopening or rebuilding the database must reproduce the bound root and counts. The database has no independent canonical, source, publication, or authority standing.

Every store read intersects the caller's admitted partitions with the object's canonical partition. Graph reachability never expands visibility. Missing permission returns absence from that caller projection and does not assert global absence.

Current publication uses two observations. `PRE_PUBLISH_MAIN` must equal the generation's exact repository commit/tree. Immediately before pointer replacement, `PRE_PUBLISH_MAIN_RECHECK` must return the same commit/tree. If main moved, the candidate is retained as historical and the current pointer is not switched. If both match, the external pointer is replaced atomically and binds the generation root and publication receipt.

WP5 retention is conservatively provisional: all content-addressed generations and publication receipts are retained. Destructive compaction is denied until WP10 measures and freezes `AtlasRetentionBudget` under the governing authority. Routine generation and pointer maintenance remain outside Git and must not create an ordinary repository PR.

G4 follow-up enforcement is mandatory. Before the first canonical `OWNS` or `GOVERNS` assertion, scope must carry an explicit `owner_role`. Before any canonical high-risk assertion, source currentness must be derived from exact repository tree/blob evidence rather than caller-authored `CURRENT`.

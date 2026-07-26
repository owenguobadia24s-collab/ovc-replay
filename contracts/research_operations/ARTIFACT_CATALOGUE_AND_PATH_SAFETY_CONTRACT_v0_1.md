# Artifact Catalogue and Path Safety Contract v0.1

Status: `FROZEN_AFTER_RO_WP2`

The artifact catalogue is read/verify/report only. It never grants publication, release, selector, or model authority.

Rules:

1. Default deny: only aliases in `RESEARCH_OPERATIONS_PATH_REGISTRY_v0_1.json` may be scanned.
2. Portable locations: persisted locations contain only `root_alias` and repository-independent `relative_path`; absolute machine paths are prohibited.
3. Traversal and symlink denial: absolute paths, `..`, root escape, symlink roots, and symlink descendants fail closed.
4. No authority by location: a file under `canonical/` is not accepted without exact declared identity and verification state.
5. No implicit network operation: GitHub Actions and R2 objects enter the catalogue only through compact descriptors or receipts; the catalogue does not fetch or upload them.
6. Deterministic inventory: the same logical roots and bytes produce the same node set and logical inventory hash.
7. Missingness is explicit: changed bytes, missing objects, expired temporary artifacts, orphan manifests, and missing dependencies remain visible as issues.
8. Validation metadata may be catalogued; Validation payload paths remain prohibited while `LOCKED_UNCONSUMED`.

# Atlas Architecture Manifest Contract v0.1

An `AtlasArchitectureManifest` is a source-bound index of design declarations
that cannot be obtained deterministically from machine-readable records. It is
not an independent semantic or authority source.

Every manifest MUST bind the complete source set used to author it by locator,
hash algorithm, exact expected hash, and role. A Core generation compares every
binding against observed source hashes and emits one
`ManifestCurrentnessRecord` state:

- `CURRENT`: every source is present and exactly matches.
- `STALE_SOURCE_HASH`: at least one present source hash differs.
- `SUPERSEDED_SOURCE`: an explicit current supersession record names the manifest.
- `UNRESOLVED`: at least one source cannot be resolved.

Only `CURRENT` declarations are eligible for later resolution. None are
canonical before WP4. Stale, superseded, and unresolved manifests remain visible
in Design/History views and cannot silently provide current declarative truth.

# Genesis Repository Topology Design v0.1

Programme: `OVC-GENESIS-REPOSITORY-TOPOLOGY-v0.1`  
Packet: `GRT-WP1`  
Status: `DESIGN_FROZEN`  
Authority: derived governance/read-model engineering only. Programme Genesis remains canonical.

## 1. Architectural decision

The repository topology has two deliberately unequal levels.

**Level 1 — Genesis canon.** Programme identity, constitutional parentage, lifecycle, authority, accepted cross-programme dependencies, migration/supersession and operator decisions remain owned by Programme Genesis and programme-owned authoritative state.

**Level 2 — Repository implementation topology.** Repository components, programme/component ownership evidence, implementation dependencies, tests, workflows, release/evidence reachability, historical reachability and anomalies are rebuilt from repository sources. This level is replaceable and authority-neutral.

A topology statement may expose a conflict with Level 1 but may never repair or reinterpret Level 1. A conflict is represented as `GENESIS_TOPOLOGY_CONFLICT` / `TOPOLOGY_CONFLICT` with both sources preserved.

## 2. Source precedence

The deterministic resolver uses this precedence, never upgrading lower evidence merely because it is convenient:

1. accepted operator decisions;
2. accepted native Genesis records;
3. programme-owned machine-readable state;
4. authority registries;
5. implementation registries;
6. release manifests and evidence records;
7. Git repository tree and commit history;
8. contracts and schemas;
9. tests, fixtures and workflows;
10. documentation and historical programme artifacts;
11. inferred structural relationships.

Inference cannot satisfy a hard Genesis prerequisite.

## 3. RepositoryComponentNode

The normal granularity is a governed package/subsystem/artifact. Individual files are materialised when they are identity-bearing, provenance-bearing, executable, contract/schema/registry/fixture/test/workflow/release evidence, or needed to detect anomalies.

Required fields:

`component_id`, `component_type`, `path`, `logical_name`, `repository`, `commit`, `blob_hash_or_tree_hash`, `owner_programme_id`, `owner_genesis_id`, `authority_state`, `implementation_state`, `lifecycle_state`, `option_or_domain`, `layer`, `version`, `schema_version`, `release_id`, `qa_state`, `freshness_state`, `historical_state`, `source_precedence`, `source_refs`, `created_from`, `last_verified_at`.

`last_verified_at` is diagnostic metadata and is excluded from logical identity.

Supported component types include `PYTHON_PACKAGE`, `PYTHON_MODULE`, `CONTRACT`, `SCHEMA`, `REGISTRY`, `FIXTURE`, `TEST`, `SCRIPT`, `TOOL`, `WORKFLOW`, `APP`, `RELEASE_RECORD`, `EVIDENCE_RECORD`, `MANIFEST`, `DECISION_RECORD`, `PROGRAMME_STATE`, `DOCUMENT`, `LEGACY_COMPONENT`, and `EXTERNAL_ARTIFACT_REFERENCE`.

Unknown classification is represented as `DOCUMENT` or `UNRESOLVED` metadata rather than guessed ownership.

## 4. RepositoryTopologyEdge

Required fields:

`edge_id`, `from_id`, `to_id`, `edge_type`, `evidence_class`, `source_ref`, `authority_effect`, `confidence_or_evidence_status`, `first_seen_commit`, `last_verified_commit`.

Supported edge types:

`IMPLEMENTS`, `OWNED_BY`, `GOVERNED_BY`, `DEFINED_BY`, `VALIDATED_BY`, `TESTED_BY`, `EXECUTED_BY`, `READS`, `WRITES`, `PRODUCES`, `CONSUMES`, `DEPENDS_ON`, `OPTIONAL_DEPENDS_ON`, `SUPERSEDES`, `SUPERSEDED_BY`, `MIGRATED_FROM`, `PROJECTS_TO`, `EXPOSED_BY`, `REFERENCES`, `DERIVED_FROM`, `SHARES_COMPONENT_WITH`.

Evidence classes, strongest to weakest for implementation evidence, are `SOURCE_EXPLICIT`, `LINEAGE_EXPLICIT`, `PATH_AND_CONTENT_CORROBORATED`, `TEST_CORROBORATED`, `IMPORT_CORROBORATED`, `CANDIDATE_RELATION`, `INFERRED`, and `UNRESOLVED`. These are not a replacement for Genesis dependency status.

All repository topology edges have `authority_effect=NONE`. Authoritative Genesis dependencies are referenced separately in the read model rather than rewritten as repository edges.

## 5. Ownership rules

Ownership is derived with explicit provenance:

- explicit programme IDs in accepted programme state, release records, contracts, registries and gate/decision evidence dominate;
- accepted PGN artifact-governance crosswalk evidence may be reused as evidence but its deferred native-adoption state is preserved;
- path/content corroboration may associate a component with a programme but cannot create programme authority;
- shared components may have multiple programme associations and `shared_component=true` without pretending to have multiple canonical owners;
- conflicting explicit owner claims produce `CONFLICTING_PROGRAMME_OWNERSHIP`;
- no defensible owner produces `owner_programme_id=null` plus `IMPLEMENTATION_WITHOUT_PROGRAMME_OWNER` where applicable;
- post-snapshot programmes are not retroactively inserted into the sealed PGN sixteen-candidate population.

## 6. ProgrammeComponentCrosswalk

For each programme visible from authoritative or preserved programme evidence, build a dossier containing programme identity reference, class/status/authority references, constitutional parent and hard-dependency references when available, and categorized component IDs for namespaces, contracts, schemas, registries, fixtures, tests, scripts, workflows, releases/evidence, console surfaces, shared components and historical components.

The crosswalk does not duplicate mutable authority truth. Authority fields are source references plus a compact projection for display.

Coverage states are `COMPLETE`, `PARTIAL`, `NO_IMPLEMENTATION`, and `UNRESOLVED`. Coverage is descriptive only.

## 7. Dependency projection

The topology maintains two distinct dependency surfaces:

- `programme_dependencies`: accepted Genesis/source-level programme dependency evidence only;
- `component_dependencies`: derived implementation relationships from explicit registries/manifests, Python imports, tests, workflows, release lineage and corroborated references.

A component import can explain implementation coupling but cannot be promoted to a hard programme prerequisite. Any attempted inferred-hard promotion is a `BLOCKER` anomaly.

## 8. Anomaly taxonomy

Required anomaly codes are frozen:

`PROGRAMME_WITHOUT_IMPLEMENTATION`, `IMPLEMENTATION_WITHOUT_PROGRAMME_OWNER`, `IMPLEMENTATION_WITHOUT_GENESIS_CROSSWALK`, `ORPHAN_CONTRACT`, `ORPHAN_SCHEMA`, `ORPHAN_REGISTRY`, `ORPHAN_FIXTURE`, `ORPHAN_TEST`, `ORPHAN_WORKFLOW`, `MISSING_CONTRACT`, `MISSING_SCHEMA`, `MISSING_FIXTURE`, `MISSING_TEST`, `MISSING_AUTHORITY_RECORD`, `MISSING_RELEASE_LINEAGE`, `DUPLICATE_COMPONENT_OWNERSHIP`, `CONFLICTING_PROGRAMME_OWNERSHIP`, `GENESIS_TOPOLOGY_CONFLICT`, `UNRESOLVED_DEPENDENCY`, `INFERRED_HARD_DEPENDENCY`, `STALE_PROGRAMME_STATE`, `STALE_DOCUMENTATION`, `SUPERSEDED_COMPONENT_STILL_REFERENCED`, `LEGACY_RUNTIME_IMPORT`, `AUTHORITY_MISMATCH`, `IMPLEMENTATION_STATE_MISMATCH`, `SHADOW_ACTIVE_MISMATCH`, `RELEASE_WITHOUT_PROGRAMME_LINEAGE`, `PROGRAMME_WITHOUT_ACCEPTED_COMPLETION_EVIDENCE`.

Severity vocabulary is exactly `INFO`, `WARNING`, `BLOCKER`. Health is a vector of exact counts and denominators; no composite score exists.

The known preflight adapter-label mismatch (`PENDING_PG_G6` text after PG-G6 explicitly deferred route/enforcement) is eligible to surface as stale-state/authority-reference evidence. It is not automatically repaired.

## 9. Identity rules

Logical component ID is a canonical hash of stable semantic fields including repository, normalized repository-relative path, component type and blob/tree identity. Logical topology identity is the canonical hash of the ordered logical read model after removing nonlogical diagnostics.

The following must not affect logical topology identity: wall-clock timestamp, hostname, absolute local path, worker identity, process ID, iteration order, filesystem traversal order, or display formatting.

Required equivalence:

`same repository commit + same Genesis snapshot + same registries + same manifests + same rule pack = same topology identity`.

The read model is replaceable. Deleting it cannot destroy authoritative information.

## 10. Scanner boundary

The scanner covers, when present: `src/`, `apps/`, `contracts/`, `schemas/`, `registries/`, `fixtures/`, `tests/`, `scripts/`, `tools/`, `.github/workflows/`, `docs/releases/`, `records/`, `plans/`, `legacy/`.

Ignored files, raw/external market payloads, caches, virtual environments and generated external-artifact stores are outside Git topology. The normal Research Operations external-artifact boundary remains the only large-artifact boundary.

## 11. Storage

Git may store contracts, schemas, rule packs, compact snapshots, crosswalks, anomaly summaries, build/QA manifests, tests and decisions. Large graph/index payloads may use the existing Research Operations external-artifact convention by reference. No second external authority store is created.

## 12. Performance model

The implementation must remain viable for hundreds of programmes, thousands of governed components and tens of thousands of repository artifacts. Measure full rebuild duration, incremental/diff duration, node count, edge count, anomaly count, peak memory where the execution environment exposes it, and serialized read-model size.

Progressive disclosure is mandatory for UI. The entire graph is never required to render at once.

## 13. Read-only operator projection

The existing Research Console remains the presentation host. GRT adds a repository-topology projection, not a fourth primary workspace. The System workspace is the preferred host and must provide read-only Portfolio, Programme, Component, Dependency, Authority, Implementation-State, Release/Evidence, Anomaly/Health, Historical/Supersession and commit-diff views.

No UI action may accept a programme, promote an edge, edit Genesis state, repair an anomaly, register a route, or write repository state.

## 14. Exact non-authorities

GRT has no authority for programme admission/adoption/reclassification, Genesis dependency acceptance, automatic remediation, Control Plane network route activation, admission enforcement, repository mutation through the operator surface, selector/model/semantic/threshold changes, releases/publication, Validation consumption, probability, risk, exposure, trading, execution or agent writes.

## 15. Reuse map

Reuse and extend:

- `ovc.programme_genesis.graph` for programme graph invariants and impact semantics;
- `ovc.programme_genesis.read_model` for derived/read-only doctrine;
- Research Operations `ArtifactCatalogue` patterns for exact repository-file provenance;
- Research Operations read-model conventions for replaceable projections;
- PGN artifact-governance crosswalk evidence classes;
- existing Research Console shell for local read-only presentation.

Do not build a competing topology service or programme registry.

## 16. GRT-G1 acceptance

GRT-G1 is auto-ratifiable only if this design introduces no competing authority registry, keeps Programme Genesis canonical, makes every topology output rebuildable, prohibits inferred edges from satisfying hard prerequisites, and prevents topology construction/presentation from altering programme state.

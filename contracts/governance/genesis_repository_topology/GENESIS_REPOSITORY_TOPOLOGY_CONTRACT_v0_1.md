# Genesis Repository Topology Contract v0.1

Programme: `OVC-GENESIS-REPOSITORY-TOPOLOGY-v0.1`

This contract implements `GRT-WP2` under accepted `GRT-G0` / `GRT-G1`. It is authority-neutral. Programme Genesis and programme-owned authoritative state remain the sole programme/dependency authority.

## Objects

The implementation SHALL materialise versioned, deterministic `RepositoryComponentNode`, `RepositoryTopologyEdge`, `ProgrammeComponentCrosswalk`, `TopologyAnomaly`, `GenesisRepositoryTopologyReadModel`, and `TopologyBuildManifest` objects using the corresponding v0.1 schemas.

Logical identities SHALL be functions only of repository-relative, source-bound logical inputs. Timestamps, hostname, absolute local path, worker/process identity, runtime duration, peak memory and display formatting SHALL NOT affect logical topology identity.

## Evidence and authority

Repository edges use evidence classes `SOURCE_EXPLICIT`, `LINEAGE_EXPLICIT`, `PATH_AND_CONTENT_CORROBORATED`, `TEST_CORROBORATED`, `IMPORT_CORROBORATED`, `CANDIDATE_RELATION`, `INFERRED`, or `UNRESOLVED` and always carry `authority_effect=NONE`.

An inferred or merely corroborated implementation dependency SHALL NOT satisfy a hard Genesis prerequisite. A hard programme dependency that is not source-explicit SHALL surface as `INFERRED_HARD_DEPENDENCY` with severity `BLOCKER`.

Ownership may be source-explicit or corroborated. Multiple plausible owners SHALL remain visible; the topology SHALL NOT guess a canonical owner.

## Rebuild and health

The read model is disposable and replaceable. Its authoritative inputs are repository/Genesis/programme sources, not the generated model itself. Health is a set of exact anomalies with exact denominators and severity `INFO`, `WARNING`, or `BLOCKER`; no composite health score is permitted.

## Scanner boundary

The rule pack defines tracked Git scan roots. External market payloads, ignored data, caches and external-artifact stores are not topology nodes unless represented by a compact governed reference committed to Git.

## Presentation boundary

Any Research Console projection is read-only. It cannot admit programmes, adopt dependencies, mutate Genesis/programme state, repair anomalies, register routes, enable enforcement, consume Validation, publish releases, or create market/probability/risk/exposure/execution authority.

## Rollback

Delete and rebuild derived topology outputs. Never rewrite upstream sources to make the topology pass.

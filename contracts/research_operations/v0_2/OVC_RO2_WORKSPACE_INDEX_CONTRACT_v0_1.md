# OVC RO2 Workspace and Observation Index Contract v0.1

Status: `IMPLEMENTED_CANDIDATE — RO2-G1 PENDING`

## Authority

This contract authorises deterministic, replaceable local indexing for approved OPT-A Discovery and Development releases. It grants no market, selector, publication, threshold, probability, exposure, trading or execution authority.

Validation remains `LOCKED_UNCONSUMED`. Validation access is metadata-only and MUST be denied before path resolution, object lookup, download, row parsing or timestamp enumeration.

## Inputs

- approved release descriptors and manifests;
- exact release and manifest hashes;
- compact observation rows supplied by an approved adapter for Discovery or Development only;
- role-access policy and dependency policy frozen at RO2-G0.

## Outputs

- `RoleWorkspaceIndex` — one entry per approved role workspace;
- `ObservationIndex` — deterministic row identity and source lineage;
- `ObservationFamilyIndex` — deterministic grouping by instrument, clock, side and schema;
- `WorkspaceAvailability` — explicit `AVAILABLE`, `METADATA_ONLY`, `NOT_AVAILABLE` or `DENIED`.

Outputs are derived, replaceable and never outrank source releases.

## Determinism

Canonical JSON uses sorted keys, UTF-8, LF line endings and compact separators. The logical index hash is SHA-256 over canonical workspace, observation and family records sorted by stable IDs. Local paths, machine names, run timestamps and process identifiers are excluded.

## Identity

- workspace ID: hash of role, release ID, manifest SHA-256, instrument and approved coverage;
- observation ID: exact upstream observation ID when present, otherwise hash of release ID, source object ID, clock, side and first-valid timestamp;
- family ID: hash of role, release ID, instrument, clock, side and observation schema version.

## Access rules

Discovery and Development may resolve approved content. Validation may expose release ID, manifest identity, aggregate counts, coverage and `LOCKED_UNCONSUMED` only. Validation content identifiers, paths, timestamps, row identities and hashes are prohibited outputs.

## Fail-closed conditions

The build MUST fail when role is unknown, a release is unapproved, manifest identity is missing, source lineage is incomplete, duplicate observation IDs conflict, a role crosses release boundaries, or Validation content resolution is attempted.

## Non-goals

No replay, quality scoring, lineage graph expansion, release comparison, console writes, Git writes, R2 writes or research-record mutation is implemented in RO2-WP1.
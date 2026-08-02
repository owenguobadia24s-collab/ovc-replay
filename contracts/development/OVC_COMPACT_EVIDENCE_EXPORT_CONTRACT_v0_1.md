# OVC Compact Evidence Export Contract v0.1

## Identity

- **contract_id:** `OVC-COMPACT-EVIDENCE-EXPORT-CONTRACT.v0.1`
- **programme_id:** `OVC-DEV-ACCEL-v0.1`
- **packet_id:** `DA-WP5`
- **gate_id:** `DA-G5`
- **status:** `ACTIVE_FOR_BOUNDED_IMPLEMENTATION`
- **authority_delta:** `COPY_ONLY_COMPACT_EVIDENCE_EXPORT`

## Purpose

Create deterministic local bundles of approved compact Development Acceleration court records so an operator can transfer or inspect them without copying raw market data, caches, credentials, private paths or mutable external state.

The exporter is mechanical only. It does not interpret evidence, change programme decisions, publish a release, write R2, access a provider, consume Validation or create market, probability, risk, exposure or execution objects.

## Inputs

An export requires:

1. the closed export profile;
2. a closed export request containing the exact source commit and an ordered inventory of source path, byte size and SHA-256;
3. a repository source root;
4. an absolute external artifact root outside the repository;
5. a destination bundle name derived from the deterministic bundle identity.

Every source must be a regular non-symlink file beneath an approved compact source root. Allowed file extensions are `.json`, `.yaml`, `.yml`, `.md` and `.txt`. Raw market formats, JSONL populations, archives, databases, binary payloads and executable files are prohibited.

## Deterministic identity

- Paths are normalized as repository-relative POSIX paths.
- Duplicate paths are prohibited.
- File bytes must match both declared byte size and SHA-256.
- Inventory order is canonical path order regardless of request order.
- The bundle identity is the canonical SHA-256 of the profile identity, source commit and normalized inventory.
- The bundle manifest is canonical JSON and records every copied byte identity.
- Machine-specific absolute paths and credentials are never written into the manifest.

## Execution

Execution is local and copy-only:

1. validate all authority, path, size, hash, extension and content-denial conditions;
2. stage beneath the external artifact root;
3. copy exact bytes into `files/<repository-relative-path>`;
4. write `manifest.json` last;
5. atomically rename the staging directory to the final immutable bundle directory.

The exporter performs no network calls, subprocess execution, repository writes, remote writes or source mutation.

## Idempotency and collision

- Re-running an identical request against an existing complete bundle returns `IDEMPOTENT_REUSE` after full manifest and byte verification.
- A pre-existing destination with a different manifest or any missing/mutated byte blocks with `DESTINATION_COLLISION`.
- Partial staging is quarantined outside the repository and is never treated as a complete bundle.

## Content denials

Execution blocks when a compact source contains credential-like material or a private absolute path. The minimum denied tokens are GitHub personal-access-token prefixes, bearer credentials, private-key headers, OpenAI project keys and Windows user-profile paths.

## Capacity

The closed profile limits each file and total bundle bytes. Capacity excess blocks before copying with `CAPACITY_EXCEEDED`; no acceptance condition may be weakened to complete an oversized export.

## Authority and destination

- The external root must be absolute, explicitly supplied and outside the repository.
- The exporter may create only its deterministic bundle and quarantine directories beneath that root.
- The exporter cannot delete accepted bundles.
- Destination configuration is operator-local and is never persisted in repository records.

## Rollback

Disable the profile or stop invoking the exporter. Preserve accepted bundles and manifests. A failed staging directory may remain quarantined for diagnosis. Do not delete accepted evidence, force-push or rewrite history.

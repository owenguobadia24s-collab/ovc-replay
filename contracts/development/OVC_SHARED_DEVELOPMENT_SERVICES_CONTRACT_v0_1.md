# OVC Shared Development Services Contract v0.1

## Authority

`LOCAL_COMPUTE_AND_GENERATED_COMPACT_RECORDS` only. The package is mechanical and policy-free. Programme profiles remain authoritative for required inputs, identities, test profiles, export profiles, paths and denied capabilities.

The package must not import market semantic implementations, modify source artifacts, publish releases, mutate selectors, write R2, consume Validation, write directly to `main`, force-push, self-approve, or create probability, risk, exposure or execution objects.

## Canonical mechanics

1. Canonical JSON uses UTF-8, sorted keys, compact separators, no NaN or infinity and no machine-specific fields.
2. Identity roles are explicit and included in logical hashes.
3. Repository-relative paths reject absolute paths, Windows drive paths, traversal, NUL, ambiguous segments and `.git` internals.
4. Artifact verification compares exact file size and SHA-256 and rejects symlinks.
5. Runtime packet profiles use strict JSON, reject unknown fields, deny all reserved authorities in v0.1 and reject duplicate logical names or paths.
6. QA aggregation is fail-closed: `QUARANTINE > BLOCK > NOT_EVALUABLE > WARN > PASS`.
7. PASS decisions require test evidence. Gate packets require acceptance conditions, tests, changed-file inventory and rollback.
8. Rollback records require preservation targets and prohibit deletion, force-push and accepted-artifact rewriting.

## Separation from later packets

DA-WP1 does not select tests, enforce execution preflight, close pull requests, write merge receipts, or export evidence. It provides deterministic types and primitives that DA-WP2–DA-WP5 may call after their own gates.

## Cross-platform guarantees

Logical identities depend only on canonical content and normalized POSIX logical paths. Local drive letters, separators, file modification times, process IDs, run timestamps and temporary directories are excluded unless a programme contract explicitly declares them as data.

## Failure behavior

Missing profile, unknown field, unsafe path, non-finite number, duplicate identity, symlink, size/hash mismatch, empty QA set, unsupported decision or destructive rollback is rejected. Failures are surfaced; the package performs no silent repair.

## Rollback

Revert the bounded DA-WP1 merge through a new non-destructive commit. Programme-specific implementations remain authoritative and may continue without the shared package. Preserve all generated QA, gate, decision and rollback records.

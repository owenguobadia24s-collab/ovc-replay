# OVC External Artifact Root Contract v0.1

## Purpose

Define the repository-to-local-storage boundary required by the OPT-A v2 programme. This contract records the path rules; implementation belongs to WP2.

## Resolution

- The process must resolve the external root from `OVC_EXTERNAL_ARTIFACT_ROOT`.
- The variable is process-local or supplied by an operator secret/configuration mechanism outside the repository.
- The repository must not persist the resolved absolute path, credentials or machine-specific drive information in source configuration.
- A missing variable is a blocking local-readiness condition, not permission to fall back into the Git worktree.
- The resolved root must be outside the repository root, must not traverse through symlinks into the repository and must be a directory controlled by the operator.

## Required logical layout

```text
OVC_EXTERNAL_ARTIFACT_ROOT/
├── intake/
├── workspace/
├── releases/
└── receipts/
```

The recommended Windows operator location is documented in the implementation programme, but code must not depend exclusively on that path.

## Storage responsibilities

Git stores contracts, schemas, registries, source code, compact manifests, QA summaries, decisions and tests.

The external root stores provider responses, mutable workspaces, frozen release payloads, local manifests and local publication/verification receipts.

Cloudflare R2 stores immutable canonical release bytes after explicit approval and full verification.

## Prohibitions

- Raw provider payloads, canonical OHLCV tables, replay streams, caches, secrets and bulky evidence ledgers may not enter Git.
- `init-workspace` may not create a frozen release root or contact a provider/R2 service.
- No workspace or release may overwrite an existing path.
- No unresolved QA, symlink, path traversal or unidentified file may be promoted into a frozen release.
- An external-root path is not evidence authority by itself; authority requires inventory, hashes, contracts, QA and gate decisions.

## WP1 state

This contract is active as governance. Resolver, workspace, freeze and readiness code remain unimplemented until WP2.
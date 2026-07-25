# OVC evidence store

`ovc_evidence_store` provides a dependency-free lifecycle for deterministic OVC evidence releases. It resolves the operator-local external artifact root, creates isolated mutable workspaces, inventories exact bytes, freezes new release roots without overwrite, builds deterministic manifests, verifies every local byte, performs non-destructive publication readiness, uploads immutable objects through rclone after exact approval, and reads every remote byte back before verification succeeds.

It never creates credentials, `.env` or `rclone.conf`. Raw market payloads remain outside Git.

## Storage planes

| Plane | Responsibility |
|---|---|
| Git | Code, contracts, schemas, registries, compact decisions, tests and lightweight receipts |
| `OVC_EXTERNAL_ARTIFACT_ROOT` | Intake responses, mutable workspaces, frozen release payloads and local receipts |
| R2 canonical | Immutable release bytes after manifest-bound operator approval |

The external root must be an absolute directory disjoint from the repository. It is resolved only from the process environment.

## Local lifecycle

```text
OVC_EXTERNAL_ARTIFACT_ROOT/
├── intake/
├── workspace/<workspace-id>/
├── releases/<release-id>/
└── receipts/
    └── freeze/<release-id>.json
```

`init-workspace` creates the external root, `intake/`, `workspace/` and one new workspace. It does not create a release directory or contact a provider/R2 service.

`inventory-workspace` emits a deterministic inventory outside the workspace. Every file is recorded by canonical POSIX-relative path, full SHA-256 and exact byte count. Symlinks, unsafe paths and case-folding collisions are rejected.

`freeze-release` requires `qa-state=PASS`, an exact approved inventory and a previously unused release ID. It copies the exact workspace inventory into a new external release root and writes a freeze receipt. Existing releases and receipts are never overwritten.

## Manifest schema

The existing schema identifier remains `ovc-evidence-release-manifest/v1`. JSON is emitted as UTF-8 with sorted object keys, compact separators, one trailing newline and no timestamp or machine-specific path.

| Field | Meaning |
|---|---|
| `schema` | Exact schema identifier |
| `release_id` | Validated immutable release namespace |
| `manifest_id` | Validated immutable manifest namespace |
| `bucket` | Bucket name and first component of every remote object path |
| `prefix` | Canonical lock prefix, without leading or trailing slash |
| `authority_state` | Authority description supplied by the operator |
| `repository_commit` | Exact source/build commit |
| `source_ref` | Source ref supplied by the operator |
| `files` | UTF-8-byte-sorted file records |

Each file record contains exactly `path`, `sha256` and `size`. Empty releases remain valid. Absolute paths, drive paths, backslashes, `.`/`..`, non-NFC names, symlinks and path collisions are rejected.

## Publication approval

The upload command requires a separate record conforming to `schemas/opt_a/opt_a_publication_approval_v0_2.json`. It must bind the exact release ID, manifest ID, manifest SHA-256, source commit, operator decision and rollback/stop note. Any changed manifest or commit invalidates the approval.

## Non-destructive readiness

`readiness` evaluates:

- release root and exact inventory;
- full local hashes and manifest schema;
- prohibited secret/temp files and symlinks;
- duplicate remote keys;
- exact source commit and clean Git worktree;
- manifest-bound publication approval;
- optional rclone remote visibility, exact-key collision state and bucket-lock visibility.

It never uploads or deletes and always reports `side_effects_performed: false`.

- `READY`: all required and supplied optional checks passed.
- `BLOCKED`: a blocking condition exists.
- `NOT_EVALUABLE`: no blocking condition was found, but remote or lock state could not be established.

## Canonical remote object keys

The retained layout is:

```text
<bucket>/<prefix>/releases/<release_id>/<manifest_id>/manifest.json
<bucket>/<prefix>/releases/<release_id>/<manifest_id>/files/<release-relative-path>
```

Uploads use `rclone copyto --immutable`. Payload files are uploaded first and the manifest is uploaded last. A collision or interrupted payload upload cannot silently overwrite retained evidence or create a completed release.

## Windows PowerShell command surface

```powershell
$env:PYTHONPATH = (Resolve-Path ".\src").Path
$env:OVC_EXTERNAL_ARTIFACT_ROOT = "C:\Users\Owner\OVIS\ovc-replay-external-artifacts"

python -m ovc_evidence_store init-workspace `
  --workspace-id <WORKSPACE_ID> --repository-root .

python -m ovc_evidence_store inventory-workspace `
  --workspace-id <WORKSPACE_ID> `
  --output <INVENTORY_JSON> --repository-root .

python -m ovc_evidence_store freeze-release `
  --workspace-id <WORKSPACE_ID> `
  --release-id <RELEASE_ID> `
  --qa-state PASS `
  --inventory <INVENTORY_JSON> `
  --repository-root .

python -m ovc_evidence_store build `
  --root <FROZEN_RELEASE_ROOT> `
  --output <MANIFEST_JSON> `
  --release-id <RELEASE_ID> `
  --manifest-id <MANIFEST_ID> `
  --bucket ovc-evidence `
  --prefix canonical `
  --authority-state CANDIDATE `
  --repository-commit <FULL_SOURCE_COMMIT> `
  --source-ref <SOURCE_REF>

python -m ovc_evidence_store verify-local `
  --manifest <MANIFEST_JSON> --root <FROZEN_RELEASE_ROOT>

python -m ovc_evidence_store readiness `
  --manifest <MANIFEST_JSON> `
  --root <FROZEN_RELEASE_ROOT> `
  --approval <PUBLICATION_APPROVAL_JSON> `
  --repository-root . `
  --remote ovc_r2 `
  --bucket-lock-visible true

python -m ovc_evidence_store upload `
  --manifest <MANIFEST_JSON> `
  --root <FROZEN_RELEASE_ROOT> `
  --remote ovc_r2 `
  --approval <PUBLICATION_APPROVAL_JSON>

python -m ovc_evidence_store verify-remote `
  --manifest <MANIFEST_JSON> --remote ovc_r2
```

WP2 implements these controls but does not authorise provider download, role-release construction, R2 publication or selector activation. See `docs/releases/opt-a-v2/governance/WP2_WINDOWS_OPERATOR_GUIDE.md` for the complete operator sequence and stop conditions.

## Tests

```powershell
$env:PYTHONPATH = (Resolve-Path ".\src").Path
python -m unittest discover -s tests -v
```

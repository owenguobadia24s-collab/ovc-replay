# WP2 Windows Operator Guide — Evidence-store lifecycle extension

## Boundary

WP2 adds safe local lifecycle and publication-readiness controls around the existing deterministic manifest, immutable upload and full-byte remote verification core. It does not download provider data, build a role release, upload to R2, activate selectors or open validation access.

Use PowerShell from the repository root with Python 3.11 or newer.

## 1. Set the process-local external root

```powershell
$env:PYTHONPATH = (Resolve-Path ".\src").Path
$env:OVC_EXTERNAL_ARTIFACT_ROOT = "C:\Users\Owner\OVIS\ovc-replay-external-artifacts"
```

Do not write this value into `.env`, `rclone.conf` or any repository file. The resolver rejects relative paths, paths inside the repository, repository-parent paths and symbolic-link traversal.

## 2. Create a mutable workspace

```powershell
python -m ovc_evidence_store init-workspace `
  --workspace-id OPT-A.GBPUSD.DISCOVERY.2021_2023.v2 `
  --repository-root .
```

`init-workspace` creates only the external `intake/` and `workspace/` planes plus the requested workspace. It does not create `releases/`, call a provider or contact R2. Existing or unsafe workspace IDs are rejected.

## 3. Build a deterministic workspace inventory

Place only approved workspace material beneath the workspace. Then write the inventory outside the workspace:

```powershell
python -m ovc_evidence_store inventory-workspace `
  --workspace-id OPT-A.GBPUSD.DISCOVERY.2021_2023.v2 `
  --output "$env:OVC_EXTERNAL_ARTIFACT_ROOT\receipts\workspace-discovery-inventory.json" `
  --repository-root .
```

The inventory records every regular file by canonical relative path, exact size and SHA-256. Symlinks, collisions and unsafe paths are rejected. Any changed, missing or additional byte invalidates the inventory.

## 4. Freeze a release locally

Freeze only after the workspace QA decision is exactly `PASS`:

```powershell
python -m ovc_evidence_store freeze-release `
  --workspace-id OPT-A.GBPUSD.DISCOVERY.2021_2023.v2 `
  --release-id OPT-A.GBPUSD.DISCOVERY.2021_2023.v2 `
  --qa-state PASS `
  --inventory "$env:OVC_EXTERNAL_ARTIFACT_ROOT\receipts\workspace-discovery-inventory.json" `
  --repository-root .
```

The command copies the exact approved inventory into a new `releases/<release-id>/` directory and writes a freeze receipt beneath `receipts/freeze/`. Existing release or receipt paths are never overwritten. Failed QA, unresolved inventory, changed bytes and symlinks stop the operation.

## 5. Build and verify the release manifest

```powershell
$releaseRoot = "$env:OVC_EXTERNAL_ARTIFACT_ROOT\releases\OPT-A.GBPUSD.DISCOVERY.2021_2023.v2"
$manifest = "$env:OVC_EXTERNAL_ARTIFACT_ROOT\receipts\MANIFEST.DISCOVERY.001.json"
$sourceCommit = (git rev-parse HEAD).Trim()

python -m ovc_evidence_store build `
  --root $releaseRoot `
  --output $manifest `
  --release-id OPT-A.GBPUSD.DISCOVERY.2021_2023.v2 `
  --manifest-id MANIFEST.DISCOVERY.001 `
  --bucket ovc-evidence `
  --prefix canonical `
  --authority-state CANDIDATE `
  --repository-commit $sourceCommit `
  --source-ref refs/heads/build/opt-a-v2-discovery-release

python -m ovc_evidence_store verify-local `
  --manifest $manifest `
  --root $releaseRoot
```

## 6. Create the publication approval record

The approval is a separate operator decision conforming to `schemas/opt_a/opt_a_publication_approval_v0_2.json`. It must bind:

- exact release ID;
- exact manifest ID;
- SHA-256 of the complete manifest file;
- exact source/build commit;
- operator identity and decision time;
- explicit rollback/stop note.

A changed manifest or source commit invalidates the approval. The approval must be stored outside the release root so it does not alter release inventory.

## 7. Run non-destructive readiness

```powershell
python -m ovc_evidence_store readiness `
  --manifest $manifest `
  --root $releaseRoot `
  --approval "$env:OVC_EXTERNAL_ARTIFACT_ROOT\receipts\publication\PUBAPP.DISCOVERY.001.json" `
  --repository-root . `
  --remote ovc_r2 `
  --bucket-lock-visible true
```

Readiness checks the exact release inventory, local hashes, manifest schema, prohibited files, symlinks, duplicate remote keys, source commit, clean Git worktree, exact publication approval, rclone visibility, exact-key collision state and supplied lock visibility.

It never calls `rclone copyto`, never uploads, never deletes and reports `side_effects_performed: false`.

- `READY`: all required and supplied optional checks passed.
- `BLOCKED`: at least one blocking check failed.
- `NOT_EVALUABLE`: no blocking failure was found, but an optional remote/lock fact could not be established.

Missing rclone configuration or unavailable lock visibility is recorded as `NOT_EVALUABLE`, not as a false success.

## 8. Upload only after separate approval

```powershell
python -m ovc_evidence_store upload `
  --manifest $manifest `
  --root $releaseRoot `
  --remote ovc_r2 `
  --approval "$env:OVC_EXTERNAL_ARTIFACT_ROOT\receipts\publication\PUBAPP.DISCOVERY.001.json"
```

The upload command now validates the exact approval before invoking the retained immutable upload core. It verifies local bytes first, uploads payload objects first and uploads the manifest last. WP2 does not authorise running this command against the programme releases; that authority belongs to WP8 after exact manifest-bound approval.

## 9. Full remote readback

```powershell
python -m ovc_evidence_store verify-remote `
  --manifest $manifest `
  --remote ovc_r2
```

Remote verification streams every object and checks the exact manifest bytes, full object sizes and SHA-256 values. It does not rely on ETags.

## Stop conditions

Stop immediately for a missing/unsafe external root, dirty worktree, changed workspace bytes, unresolved inventory, QA state other than `PASS`, existing release path, manifest or approval mismatch, symlink, prohibited file, remote collision, absent publication authority or failed remote verification.

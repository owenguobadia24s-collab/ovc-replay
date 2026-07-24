# OVC evidence store

`ovc_evidence_store` builds deterministic evidence-release manifests, verifies
every local byte, uploads immutable objects through rclone, and reads every
remote object back before declaring verification successful. It uses only the
Python standard library and never creates credentials, `.env`, or
`rclone.conf`.

## Manifest schema

The schema identifier is `ovc-evidence-release-manifest/v1`. JSON is emitted as
UTF-8 with sorted object keys, compact separators, one trailing newline, and no
timestamp or machine-specific path. The top-level fields are:

| Field | Meaning |
| --- | --- |
| `schema` | Exact schema identifier |
| `release_id` | Validated immutable release namespace |
| `manifest_id` | Validated immutable manifest namespace |
| `bucket` | Intended bucket name (provenance; rclone selects the endpoint) |
| `prefix` | Canonical lock prefix, without leading or trailing slash |
| `authority_state` | Authority description supplied by the operator |
| `repository_commit` | Source repository commit supplied by the operator |
| `source_ref` | Source ref supplied by the operator |
| `files` | UTF-8-byte-sorted file records |

Each file record has exactly `path`, `sha256`, and `size`. `path` is a
root-relative, NFC-normalized POSIX path. `size` is the exact byte count and
`sha256` is the lowercase digest of the complete file.

Empty releases are valid. Symbolic links, absolute paths, drive paths,
backslashes, `.`/`..` components, non-NFC names, and case-folding path
collisions are rejected.

## Canonical remote object keys

The layout is fixed before upload:

```text
<prefix>/releases/<release_id>/<manifest_id>/manifest.json
<prefix>/releases/<release_id>/<manifest_id>/files/<release-relative-path>
```

When `prefix` is empty, the key begins with `releases/`. Both identifiers are
restricted to safe ASCII segments. The separate `files/` boundary prevents a
release path from colliding with the manifest. The pair
`release_id/manifest_id` gives every manifest its own immutable namespace.

Uploads use `rclone copyto --immutable`. Under an indefinite R2 bucket-lock
prefix, first publication succeeds; an attempted overwrite or identifier reuse
fails rather than replacing retained evidence. Choose a new `manifest_id` for
every distinct manifest. The `--remote` argument is an already configured
rclone remote name; no configuration is written by this package.

## Windows PowerShell

Use Python 3.11 or newer. From the repository root, an editable install is
optional; the examples below use the src layout directly:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src)

python -m ovc_evidence_store build `
  --root .\path\to\release `
  --output .\path\to\release-manifest.json `
  --release-id release-2026-07 `
  --manifest-id manifest-001 `
  --bucket ovc-evidence `
  --prefix locked/ovc `
  --authority-state ratified `
  --repository-commit 0123456789abcdef `
  --source-ref refs/heads/build

python -m ovc_evidence_store verify-local `
  --manifest .\path\to\release-manifest.json `
  --root .\path\to\release

# Rclone must already be configured outside this repository.
$env:OVC_RCLONE_REMOTE = 'r2-evidence'

python -m ovc_evidence_store upload `
  --manifest .\path\to\release-manifest.json `
  --root .\path\to\release `
  --remote $env:OVC_RCLONE_REMOTE

python -m ovc_evidence_store verify-remote `
  --manifest .\path\to\release-manifest.json `
  --remote $env:OVC_RCLONE_REMOTE
```

`upload` first performs full local verification. `verify-remote` uses
`rclone cat` to read the exact remote manifest and every complete release
object; it checks manifest byte identity and each file's byte count and
SHA-256. All validation, filesystem, and rclone failures produce a clear
stderr message and a non-zero process exit code.

Run all tests in PowerShell with:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src)
python -m unittest discover -s tests -v
```

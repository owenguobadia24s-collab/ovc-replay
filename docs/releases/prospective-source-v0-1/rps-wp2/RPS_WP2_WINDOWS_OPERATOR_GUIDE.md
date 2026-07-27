# RPS-WP2 — Windows Operator Guide

## Authority boundary

This guide executes only the RPS-G1-approved local intake:

- provider: `DUKASCOPY`
- instrument: `GBPUSD`
- slice: `RPS.DUKASCOPY.GBPUSD.20260724_20260727.v1`
- half-open source window: `[2026-07-24T00:00:00Z, 2026-07-27T00:00:00Z)`
- logical streams: `M1_BID`, `M1_ASK`, `H1_BID`, `H1_ASK`
- compressed-byte limit: `26214400`
- expanded-byte limit: `104857600`

The command creates a local-only immutable source slice. It does **not** create an OPT-A release, change a selector, write to R2, consume Validation, append LIVE_PROSPECTIVE evidence or activate Pattern Discovery triage.

Provider execution is explicitly denied when `CI` or `GITHUB_ACTIONS` is true.

## 1. Update the local repository

Run PowerShell from the repository root:

```powershell
cd C:\Users\Owner\OVIS\ovc-replay

git switch main
git pull --ff-only
git status --short
```

The worktree must be clean before execution.

## 2. Prepare Python

The repository supports Python 3.11 or newer. Use the existing virtual environment when present:

```powershell
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
}

$python = ".\.venv\Scripts\python.exe"
& $python -m pip install -e .
$env:PYTHONPATH = (Resolve-Path ".\src").Path
```

Activation is optional because the wrapper resolves `.venv\Scripts\python.exe` directly.

## 3. Set the external artifact root

The path must be absolute, outside the repository and outside any repository parent/child relationship:

```powershell
$env:OVC_EXTERNAL_ARTIFACT_ROOT = `
    "C:\Users\Owner\OVIS\ovc-replay-external-artifacts"

New-Item `
    -ItemType Directory `
    -Force `
    -Path $env:OVC_EXTERNAL_ARTIFACT_ROOT |
    Out-Null
```

Do not persist this machine path in Git, `.env`, repository configuration or receipts.

## 4. Run the no-network preflight

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\run_rps_wp2_intake.ps1 -Command preflight
```

Expected state:

```text
status: READY_FOR_OPERATOR_LOCAL_EXECUTION
slice_id: RPS.DUKASCOPY.GBPUSD.20260724_20260727.v1
provider_network_access_performed: false
```

Preflight rejects a non-empty existing destination. An empty directory created during earlier setup is accepted and removed immediately before the staged run begins.

## 5. Execute the exact provider intake

This is the only command that contacts Dukascopy:

```powershell
.\scripts\run_rps_wp2_intake.ps1 -Command execute
```

The wrapper binds execution to `RPS-G1`. The Python module contains no arguments for changing the slice, dates, streams or limits.

The adapter reuses the existing direct Dukascopy BI5 candle format and request policy:

- daily M1 BID and ASK transport partitions for 24–26 July 2026;
- monthly native-H1 BID and ASK transport partitions, filtered to the exact approved interval;
- exact compressed transport bytes retained outside Git;
- zero-volume equal-OHLC flats removed only under the frozen adapter policy;
- accepted logical source objects written as deterministic UTF-8 CSV.

The monthly H1 endpoint is a provider transport partition. Only rows inside the approved half-open interval enter the four logical source objects.

## 6. Successful output

The final source slice is created only after all checks pass:

```text
%OVC_EXTERNAL_ARTIFACT_ROOT%/
  prospective-source/
    intake/
      RPS.DUKASCOPY.GBPUSD.20260724_20260727.v1/
        transport/
        source-objects/
          GBPUSD_M1_BID_20260724_20260727_UTC.csv
          GBPUSD_M1_ASK_20260724_20260727_UTC.csv
          GBPUSD_H1_BID_20260724_20260727_UTC.csv
          GBPUSD_H1_ASK_20260724_20260727_UTC.csv
        receipts/
          provider-request-receipt.json
          source-object-inventory.json
          gap-and-duplicate-qa.json
          bid-ask-reconciliation.json
          native-h1-reconciliation.json
          freeze-receipt.json
        source-slice-manifest.json
```

The compact receipts record:

- provider transport IDs, status, byte size and SHA-256;
- four logical source-object IDs, byte sizes, row counts and SHA-256;
- strict ordering and duplicate results;
- exact first and last expected timestamps;
- weekend-spanning discontinuities separately from unexpected intra-session gaps;
- exact BID/ASK timestamp pairing and price-order checks;
- M1-derived complete-H1 versus native-H1 OHLC reconciliation;
- manifest logical hash and complete manifest-file hash;
- `NOT_A_RELEASE`, selector `NONE`, R2 `DENIED`, Validation `DENIED` and LIVE_PROSPECTIVE append `DENIED`.

The manifest logical hash is calculated over the canonical manifest fields before `manifest_sha256` is inserted. The freeze receipt separately records the SHA-256 of the complete manifest file.

## 7. Failure and quarantine behaviour

Any of the following prevents an accepted source slice:

- request outside the compiled RPS-G1 scope;
- CI or GitHub Actions execution;
- missing or unsafe external root;
- provider transport failure;
- invalid BI5/LZMA bytes;
- compressed bytes above 25 MiB;
- expanded workspace above 100 MiB;
- empty logical stream;
- incomplete start/end boundary coverage;
- duplicate or non-monotonic timestamps;
- unexpected intra-session gap;
- BID/ASK timestamp or price-order mismatch;
- no complete M1-derived H1 comparison;
- native-H1 OHLC mismatch;
- existing non-empty destination;
- attempted overwrite.

The mutable staging workspace is moved beneath:

```text
%OVC_EXTERNAL_ARTIFACT_ROOT%/prospective-source/intake/quarantine/
```

It receives an incident record where possible. No accepted `source-slice-manifest.json` is created at the approved destination. Do not repair, fill or edit provider rows. Preserve the quarantine and return the error and compact incident details for review.

## 8. Verify repository separation

After a successful or quarantined run:

```powershell
git status --short --untracked-files=all
```

No BI5, CSV, provider response, machine path, cache or large evidence file may appear in Git.

## 9. Continue RPS-WP2

Provide only these compact files from the accepted slice:

- `source-slice-manifest.json`
- all files under `receipts/`

Then issue:

```text
@GitHub OVC CONTINUE
```

RPS-G2 remains blocked until the compact evidence proves that the exact immutable local source slice is reproducible.

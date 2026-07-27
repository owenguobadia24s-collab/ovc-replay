# RPS-WP2 — Windows Operator Guide (RPS-G1A Candidate)

## Approval boundary

This guide is prepared for the consolidated `RPS-G1A` operator amendment gate. Until that gate is approved, the replacement provider request must not be executed.

The proposed replacement intake is fixed to:

- provider: `DUKASCOPY`
- instrument: `GBPUSD`
- slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`
- half-open source window: `[2026-06-22T00:00:00Z, 2026-06-25T00:00:00Z)`
- logical streams: `M1_BID`, `M1_ASK`, native `H1_BID`, native `H1_ASK`
- compressed-byte limit: `26214400`
- expanded-byte limit: `104857600`

The original July scope is preserved as a quarantined provider-availability incident. Its identity and bytes are not reusable for this replacement slice.

The command creates only a local immutable source slice. It does **not** create an OPT-A release, change a selector, write to R2, consume Validation, append LIVE_PROSPECTIVE evidence or activate Pattern Discovery triage.

Provider execution is explicitly denied when `CI` or `GITHUB_ACTIONS` is true.

## 1. After RPS-G1A approval, update the repository

Run PowerShell from the repository root:

```powershell
cd C:\Users\Owner\OVIS\ovc-replay

git switch main
git pull --ff-only
git status --short
```

The worktree must be clean before execution. Confirm that `main` contains the approved RPS-G1A merge before proceeding.

## 2. Prepare Python

The repository supports Python 3.11 or newer:

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

The path must be absolute and disjoint from the repository:

```powershell
$env:OVC_EXTERNAL_ARTIFACT_ROOT = `
    "C:\Users\Owner\OVIS\ovc-replay-external-artifacts"

New-Item `
    -ItemType Directory `
    -Force `
    -Path $env:OVC_EXTERNAL_ARTIFACT_ROOT |
    Out-Null
```

Do not persist the machine path in Git, `.env`, repository configuration or compact receipts.

## 4. Preserve the July quarantine

Do not delete, rename into the June identity, or copy provider bytes from the quarantined July attempt into the June destination.

The replacement destination is:

```text
%OVC_EXTERNAL_ARTIFACT_ROOT%/prospective-source/intake/
RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1/
```

The previous July quarantine remains under the operator-local quarantine directory and is governed by `RPS_G1A_PROVIDER_AVAILABILITY_INCIDENT.md`.

## 5. Run the no-network preflight

After approval and merge:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\run_rps_wp2_intake.ps1 -Command preflight
```

Expected state:

```text
status: READY_FOR_OPERATOR_LOCAL_EXECUTION
gate: RPS-G1A
slice_id: RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1
source_window_start_utc: 2026-06-22T00:00:00Z
source_window_end_utc: 2026-06-25T00:00:00Z
provider_network_access_performed: false
```

Preflight rejects a non-empty existing replacement destination. An absent or completely empty destination is valid.

## 6. Execute the exact replacement intake

This is the only command that contacts Dukascopy:

```powershell
.\scripts\run_rps_wp2_intake.ps1 -Command execute
```

The wrapper binds execution to `RPS-G1A` and the module:

```text
ovc.research_operations.prospective_source.dukascopy_intake_rps_g1a
```

The command has no CLI options for changing the slice, dates, streams or byte limits.

The adapter uses:

- daily M1 BID and ASK transport partitions for 22–24 June 2026;
- completed-month native-H1 BID and ASK transport partitions for June 2026, filtered to the exact half-open interval;
- exact compressed transport bytes retained outside Git;
- deterministic UTF-8 CSV logical objects;
- zero-volume equal-OHLC flat removal only under the frozen adapter policy.

The monthly H1 endpoint is only a transport partition. Only rows inside the approved three-day interval enter the four logical source objects.

## 7. Successful output

The final source slice is created only after all checks pass:

```text
%OVC_EXTERNAL_ARTIFACT_ROOT%/
  prospective-source/
    intake/
      RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1/
        transport/
        source-objects/
          GBPUSD_M1_BID_20260622_20260625_UTC.csv
          GBPUSD_M1_ASK_20260622_20260625_UTC.csv
          GBPUSD_H1_BID_20260622_20260625_UTC.csv
          GBPUSD_H1_ASK_20260622_20260625_UTC.csv
        receipts/
          provider-request-receipt.json
          source-object-inventory.json
          gap-and-duplicate-qa.json
          bid-ask-reconciliation.json
          native-h1-reconciliation.json
          freeze-receipt.json
        source-slice-manifest.json
```

The compact records include:

- provider transport identities, status, byte size and SHA-256;
- four source-object identities, byte sizes, row counts and SHA-256;
- strict ordering and duplicate results;
- exact first and last expected timestamps;
- unexpected intra-session gap results;
- exact BID/ASK timestamp pairing and price-order checks;
- M1-derived complete-H1 versus native-H1 OHLC reconciliation;
- manifest logical hash and complete manifest-file hash;
- `NOT_A_RELEASE`, selector `NONE`, R2 `DENIED`, Validation `DENIED` and LIVE_PROSPECTIVE append `DENIED`.

## 8. Failure and quarantine behavior

Any of the following prevents an accepted source slice:

- gate other than `RPS-G1A`;
- CI or GitHub Actions execution;
- missing or unsafe external root;
- provider transport failure;
- invalid BI5/LZMA bytes;
- compressed bytes above 25 MiB;
- expanded workspace above 100 MiB;
- empty logical stream;
- incomplete start/end boundary coverage;
- duplicate or non-monotonic timestamps;
- unexpected gap;
- BID/ASK mismatch or inversion;
- no complete M1-derived H1 comparison;
- native-H1 OHLC mismatch;
- existing non-empty destination;
- attempted overwrite.

A failure creates no accepted source slice. The staging workspace is moved into the local quarantine directory with an incident record.

## 9. Return compact evidence only

After a successful freeze, provide only:

```text
source-slice-manifest.json
receipts/provider-request-receipt.json
receipts/source-object-inventory.json
receipts/gap-and-duplicate-qa.json
receipts/bid-ask-reconciliation.json
receipts/native-h1-reconciliation.json
receipts/freeze-receipt.json
```

Do not attach or commit:

- BI5 transport files;
- source-object CSV files;
- caches;
- the external-artifact root;
- absolute machine paths;
- provider credentials;
- quarantine payloads.

Then issue:

```text
@GitHub OVC CONTINUE
```

RPS-G2 remains blocked until the compact accepted-slice evidence is reproducible.

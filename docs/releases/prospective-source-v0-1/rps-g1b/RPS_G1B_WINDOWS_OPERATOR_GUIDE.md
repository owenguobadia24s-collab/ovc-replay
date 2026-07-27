# RPS-G1B Windows Operator Guide

## Authority boundary

Use this guide only after `RPS-G1B` receives operator PASS and its bounded implementation is present on `main`.

The command performs no provider request. It reads the exact June RPS-G1A quarantine, creates a checksum inventory outside that quarantine, copies verified transport bytes to a new staging workspace, re-evaluates the frozen GAPPED contract and freezes the existing June slice identity only if every condition passes.

It cannot accept another quarantine ID, slice, interval, instrument, side, clock, row count or gap count through command-line options.

## 1. Update the local checkout

```powershell
cd C:\Users\Owner\OVIS\ovc-replay

git switch main
git pull --ff-only
git status --short
```

The worktree must be clean.

## 2. Set the external artifact root

```powershell
$env:OVC_EXTERNAL_ARTIFACT_ROOT = `
    "C:\Users\Owner\OVIS\ovc-replay-external-artifacts"
```

The exact source quarantine must remain at:

```text
%OVC_EXTERNAL_ARTIFACT_ROOT%/prospective-source/intake/quarantine/
RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1.20260727T160337Z.38a69acd/
```

Do not rename, move, edit or add files to that directory.

## 3. Preflight

```powershell
.\scripts\run_rps_wp2_intake.ps1 -Command preflight
```

Expected status:

```text
READY_FOR_CHECKSUM_INVENTORY
```

Preflight verifies the exact quarantine identity, the incident record, the eight expected transport objects, observed byte sizes and the absence of unexpected files. It performs no provider access and no mutation.

## 4. Freeze the checksum inventory

```powershell
.\scripts\run_rps_wp2_intake.ps1 -Command inventory
```

Expected status:

```text
CHECKSUM_INVENTORY_FROZEN
```

The inventory is written outside the source quarantine under:

```text
%OVC_EXTERNAL_ARTIFACT_ROOT%/prospective-source/intake/recovery/
RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1.20260727T160337Z.38a69acd/
quarantine-checksum-inventory.json
```

It contains the exact relative path, byte size and SHA-256 for the incident record and all eight transport objects, plus a canonical inventory SHA-256.

If this command has already succeeded, do not overwrite the inventory. Preserve it and proceed only if its identity is known and the source quarantine has not changed.

## 5. Re-evaluate and freeze

```powershell
.\scripts\run_rps_wp2_intake.ps1 -Command freeze
```

Expected successful status:

```text
FROZEN_LOCAL_GAPPED_SOURCE_SLICE
```

The command requires exact gate binding `RPS-G1B`, denies execution in CI, performs no network access and creates no provider retry.

## Acceptance checks

The freeze succeeds only when:

- M1 BID and ASK each contain 4,285 rows;
- both sides expose the same 35 absent timestamps in 24 gap runs;
- boundaries are complete and ordering is strict;
- native H1 BID and ASK contain 72 rows and pair exactly;
- 64 complete M1-derived H1 bars per side match native H1 OHLC exactly;
- every incomplete 15M, M1-derived H1 and 2H parent is explicitly unavailable;
- no repair, fill, interpolation or synthesis occurs;
- the source quarantine remains byte-identical before and after copy.

## Accepted output

```text
%OVC_EXTERNAL_ARTIFACT_ROOT%/prospective-source/intake/
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
    downstream-coverage-propagation.json
    quarantine-checksum-inventory.json
    freeze-receipt.json
  source-slice-manifest.json
```

The manifest must state `coverage_state: GAPPED`, `NOT_A_RELEASE`, selector `NONE` and R2 `DENIED`.

## Failure handling

On any re-evaluation failure, the new recovery staging workspace is moved to a separate local quarantine. The original RPS-G1A June quarantine remains untouched. Gap, BID/ASK, native-H1 and downstream-coverage receipts are written before the pass/fail branch and therefore remain available in the recovery-failure quarantine.

Do not edit a failed staging quarantine and do not weaken or bypass the checks.

## Compact continuation evidence

After a successful freeze, provide only:

- `source-slice-manifest.json`;
- the eight files under `receipts/`.

Do not upload BI5 transport objects, CSV source objects, local machine paths or the original quarantine directory to Git.

Then issue:

```text
@GitHub OVC CONTINUE
```

RPS-G2 remains unavailable until the compact evidence is reproduced and accepted.

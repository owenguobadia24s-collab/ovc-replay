# PD-JUNE-FULL-MONTH-MDR Windows Operator Guide

## Purpose

Execute the approved read-only source intake for the whole-June assessment after the tooling PR is merged into `main`.

The command fetches context from May 30 through July 2 inclusive, but only June 1 through June 30 is target-eligible. May and July remain context-only.

## Source and target

- target: `2026-06-01T00:00:00Z` to `2026-07-01T00:00:00Z`, end exclusive
- source context: `2026-05-30T00:00:00Z` to `2026-07-03T00:00:00Z`, end exclusive
- source slice: `RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1`
- gate binding: `PD-JUNE-FM-G1`

## PowerShell commands

```powershell
cd C:\Users\Owner\OVIS\ovc-replay

git checkout main
git pull --ff-only

$env:OVC_EXTERNAL_ARTIFACT_ROOT = 'C:\Users\Owner\OVIS\ovc-replay-external-artifacts'

.\scripts\run_pd_june_full_month_mdr.ps1 profile
.\scripts\run_pd_june_full_month_mdr.ps1 plan
.\scripts\run_pd_june_full_month_mdr.ps1 preflight
.\scripts\run_pd_june_full_month_mdr.ps1 execute
```

Do not run `execute` until `preflight` returns `READY_FOR_OPERATOR_LOCAL_EXECUTION`.

## Expected destination

```text
C:\Users\Owner\OVIS\ovc-replay-external-artifacts\
  prospective-source\intake\
  RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1\
```

The destination must be absent or empty before execution. The intake refuses to overwrite existing material.

## Expected compact return artifacts

Return these files for repository validation:

```text
source-slice-manifest.json
receipts\provider-request-plan.json
receipts\provider-request-receipt.json
receipts\source-object-inventory.json
receipts\coverage-gap-duplicate-qa.json
receipts\bid-ask-reconciliation.json
receipts\native-h1-reconciliation.json
receipts\freeze-receipt.json
```

Do not stage or upload raw provider transports, source CSVs, caches or large replay outputs into Git.

## Acceptance

The execution succeeds only when:

- all required native H1 monthly transports are available;
- BID and ASK timestamps match exactly;
- rows are unique and strictly increasing;
- every non-weekend intra-session gap is absent;
- weekend or documented closure discontinuities are explicit;
- complete M1-derived H1 bars match native H1 OHLC exactly;
- byte limits are respected;
- the final manifest is frozen as `NOT_A_RELEASE`, selector-ineligible, R2-denied and Validation-denied.

Any failure is quarantined under the local external artifact root. Do not delete quarantine evidence.
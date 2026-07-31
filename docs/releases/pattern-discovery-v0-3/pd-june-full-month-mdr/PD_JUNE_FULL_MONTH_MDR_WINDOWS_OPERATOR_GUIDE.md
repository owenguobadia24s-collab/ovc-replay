# PD-JUNE-FULL-MONTH-MDR Windows Operator Guide

## Purpose

Execute the approved read-only source intake for the whole-June assessment after amendment `PD-JUNE-FM-A1-JULY-NATIVE-H1-WAIVER` is merged into `main`.

The command fetches context from May 30 through July 2 inclusive, but only June 1 through June 30 is target-eligible. May and July remain context-only.

The unavailable July monthly native-H1 transport is no longer requested. July 1–2 M1 context remains mandatory and is deterministically aggregated into H1 only when every hour has 60 distinct M1 members.

## Source and target

- target: `2026-06-01T00:00:00Z` to `2026-07-01T00:00:00Z`, end exclusive
- source context: `2026-05-30T00:00:00Z` to `2026-07-03T00:00:00Z`, end exclusive
- source slice: `RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1`
- gate binding: `PD-JUNE-FM-G1`
- provider request count: 72
- daily M1 requests: 68, including July 1–2
- native H1 monthly requests: 4, May and June only
- native July H1: `WAIVED_BY_OPERATOR_A1_PROVIDER_OBJECT_UNAVAILABLE`
- July context H1: `M1_DERIVED_FROM_COMPLETE_JULY_CONTEXT_BARS`

## Preserve the failed attempt

Do not delete or reuse this quarantined incident:

```text
RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1.20260731T152217Z.86351858
```

It is historical evidence of the unavailable native July H1 provider object and is not an accepted source slice.

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

Do not run `execute` until `preflight` returns `READY_FOR_OPERATOR_LOCAL_EXECUTION`, reports `provider_object_count: 72`, and records the July native-H1 waiver.

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

- all 68 M1 daily transports and the four required May/June native H1 monthly transports satisfy the approved intake rules;
- no July native H1 provider object is requested;
- exactly 48 complete July 1–2 H1 context hours are derived per side from complete M1 membership;
- BID and ASK timestamps match exactly for M1 and the combined H1 stream;
- rows are unique and strictly increasing;
- every non-weekend intra-session gap is absent;
- weekend or documented closure discontinuities are explicit;
- complete M1-derived H1 bars match native May/June H1 OHLC exactly;
- no interpolation, forward fill, repair or silent row insertion occurs;
- byte limits are respected;
- the final manifest records mixed H1 provenance as `NATIVE_MAY_JUNE_PLUS_M1_DERIVED_JULY_CONTEXT`;
- the final manifest is frozen as `NOT_A_RELEASE`, selector-ineligible, R2-denied and Validation-denied.

Any failure is quarantined under the local external artifact root. Do not delete quarantine evidence.

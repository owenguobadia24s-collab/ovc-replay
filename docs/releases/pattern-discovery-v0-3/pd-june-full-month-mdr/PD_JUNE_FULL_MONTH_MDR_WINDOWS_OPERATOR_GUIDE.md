# PD-JUNE-FULL-MONTH-MDR Windows Operator Guide

## Current authority

Execute the whole-June source intake under both approved amendments:

- `PD-JUNE-FM-A1-JULY-NATIVE-H1-WAIVER`
- `PD-JUNE-FM-A2-PAIRED-SPARSE-M1-ACCEPTANCE`

The target remains June 2026. May and July are context-only. July native H1 is not requested.

A2 permits provider-observed absent M1 timestamps only when BID and ASK timestamp sets are exactly identical. No missing candle may be repaired or synthesised. Every incomplete 15M, H1 or 2H bucket is non-evaluable and no candidate window may bridge it.

## Preserved evidence

Do not delete or reuse either quarantine:

```text
RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1.20260731T152217Z.86351858
RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1.20260731T162043Z.fe725d23
```

The second quarantine is the source of the A2 diagnostic. It is not an accepted source slice.

## PowerShell

```powershell
cd C:\Users\Owner\OVIS\ovc-replay

git checkout main
git pull --ff-only

$env:OVC_EXTERNAL_ARTIFACT_ROOT = 'C:\Users\Owner\OVIS\ovc-replay-external-artifacts'

.\scripts\run_pd_june_full_month_mdr.ps1 profile
.\scripts\run_pd_june_full_month_mdr.ps1 plan
.\scripts\run_pd_june_full_month_mdr.ps1 preflight
```

Preflight must report:

```text
plan_amendment: PD-JUNE-FM-A2-PAIRED-SPARSE-M1-ACCEPTANCE
amendment_gate: PD-JUNE-FM-A2-PAIRED-SPARSE-M1-ACCEPTANCE
provider_object_count: 72
paired_sparse_m1_policy: ACCEPT_EXACTLY_PAIRED_PROVIDER_ABSENCE_WITH_EXPLICIT_CENSORING
downstream_incomplete_membership_policy: INCOMPLETE_REQUIRED_MEMBERSHIP_NOT_EVALUABLE_NO_BRIDGING
status: READY_FOR_OPERATOR_LOCAL_EXECUTION
```

Then run:

```powershell
.\scripts\run_pd_june_full_month_mdr.ps1 execute
```

## Acceptance

The A2 run may freeze only when:

- M1 BID and ASK timestamp sets are exactly identical;
- combined H1 BID and ASK timestamp sets are exactly identical;
- duplicates and non-monotonic rows are zero;
- all gap runs and absent timestamps are explicit;
- native May/June H1 matches every complete M1-derived H1 bar;
- incomplete July context hours are censored, not repaired;
- no interpolation, fill, copied close, synthetic candle or continuity bridging occurs;
- provider execution remains local-only;
- the slice remains non-release, selector-ineligible, R2-denied and Validation-denied.

## Return artifacts

Upload only:

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

Do not stage raw transports, source CSVs, caches or replay outputs.

# PD-JUNE-FM-WP2 Windows Operator Guide

## Purpose

Run the approved deterministic C1/C2 replay over the accepted full-month source slice after the WP2 tooling PR is squash-merged into `main`.

The replay performs no provider network access. It verifies the frozen source slice under `OVC_EXTERNAL_ARTIFACT_ROOT`, derives 15M and 2H bars from M1, applies the existing C1 formulas and C2 engines, preserves May and July as context, and marks only June records as target-eligible.

## Frozen identities

- programme: `PD-JUNE-FULL-MONTH-MDR`
- packet: `PD-JUNE-FM-WP2`
- source slice: `RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1`
- source manifest: `1578b555f3d5aa2822b603141261f86a047096030e5faacd4380ef2c6d4f52e3`
- authority binding: `PD-JUNE-FM-G1`
- target: `2026-06-01T00:00:00Z` to `2026-07-01T00:00:00Z`, end exclusive
- source context: `2026-05-30T00:00:00Z` to `2026-07-03T00:00:00Z`, end exclusive

## PowerShell

```powershell
cd C:\Users\Owner\OVIS\ovc-replay

git checkout main
git pull --ff-only

$env:OVC_EXTERNAL_ARTIFACT_ROOT = `
  'C:\Users\Owner\OVIS\ovc-replay-external-artifacts'

.\scripts\run_pd_june_full_month_mdr_wp2.ps1 preflight
```

Preflight must return:

```text
READY_FOR_OPERATOR_LOCAL_FULL_MONTH_C1_C2_REPLAY
```

It must also report:

- repository branch `main`;
- verified source manifest identity;
- 34,565 M1 rows per side;
- target and context boundaries above;
- provider network access `false`;
- replay execution in CI denied.

Then run:

```powershell
.\scripts\run_pd_june_full_month_mdr_wp2.ps1 execute
```

## Expected output location

```text
C:\Users\Owner\OVIS\ovc-replay-external-artifacts\
  prospective-source\compute\
  PD-JUNE-FM.RUN.<deterministic-id>\
```

The command refuses to overwrite an existing run identity. A failed staging workspace is quarantined rather than deleted.

## Expected compact return files

Return only these compact files for repository acceptance:

```text
output-manifest.json
replay-run.json
prospective-source-binding.json
replay-receipt.json
payload\qa\coverage.json
payload\qa\target-eligibility.json
```

Do not upload or stage the JSONL replay payloads, source CSVs, raw BI5 files, caches, or other large external artifacts in Git.

## Acceptance expectations

The local run must prove:

- exact frozen source and source-object hash binding;
- exactly paired sparse BID/ASK membership;
- 15M and 2H incomplete parent sets censored without repair or bridging;
- C1 state reset at every incomplete-bar discontinuity;
- C2 state reset at every discontinuity;
- 2H parent context invalidated after an incomplete parent until a new complete parent is first-valid;
- May and July retained only as context;
- June target filtering applied after full-interval replay;
- zero insufficiency caused solely by the June calendar boundary;
- byte-identical independent rerun payloads;
- unchanged C1 formula registry and active C2 model identity;
- no release, selector, R2, Validation, live append, risk, trading, execution, or agent-write authority.

## Failure handling

Do not weaken tests, bridge gaps, fill absent prices, or relabel quarantined output. Preserve the source slice and any quarantined replay staging directory, then return the failure receipt and error text for bounded correction.

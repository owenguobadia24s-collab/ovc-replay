# RO-WP2 Windows Operator Guide

## Status

`APPROVED_BOUNDED_LOCAL_OPERATION_RO_G2_PASS`

RO-G2 approved the RO-WP2 CLI, append-only service, audit service, artifact catalogue, and operating queues for bounded local use. This does not create active-research, market, probability, exposure, execution, or agent authority.

RO-WP2 performs no Git commit or push, provider download, R2 upload or deletion, selector mutation, threshold change, model classification, or Validation payload access.

## Environment

Use PowerShell and set machine-local paths only in the process environment or a secret manager:

```powershell
$env:OVC_REPOSITORY_ROOT = "C:\Users\Owner\OVIS\ovc-replay"
$env:OVC_EXTERNAL_ARTIFACT_ROOT = "C:\Users\Owner\OVIS\ovc-replay-external-artifacts"
$env:OVC_RESEARCH_OPERATOR_ID = "Owen Vitae"
$env:OVC_SOURCE_COMMIT = "<exact repository commit>"
```

Do not commit those absolute paths.

## Launch

```powershell
.\scripts\start_research_operations.ps1 --help
.\scripts\start_research_operations.ps1 research open-session --help
```

The launcher sets `PYTHONPATH` to the repository `src` directory and calls `python -m ovc`.

## Example bounded workflow

```powershell
.\scripts\start_research_operations.ps1 research open-session `
  --instrument GBPUSD `
  --release OPT-A.GBPUSD.DISCOVERY.2021_2023.v2 `
  --role DISCOVERY `
  --cutoff 2023-06-15T10:00:00Z `
  --objective "Describe the current 2H structure without later-path access"
```

Use the returned draft ID with `add-observation`, then freeze through `freeze-observation`. Claims, realizations, adjudications and close-session actions create append-only frozen records and immutable audit events.

## Artifact catalogue

```powershell
.\scripts\start_research_operations.ps1 artifact scan `
  --root-alias repo_contracts `
  --root-alias repo_schemas `
  --root-alias repo_registries

.\scripts\start_research_operations.ps1 artifact report
```

The catalogue stores only root aliases and relative paths. It rejects absolute traversal and unsafe symlinks. GitHub Actions and R2 objects are represented only by compact descriptors or receipts; the catalogue makes no network request.

## Recovery

`var\research_operations\` contains derived drafts and catalogue state and may be rebuilt. Frozen compact records under `records\research_operations\` are append-only. Never repair a frozen record in place; create a superseding record.

Validation remains metadata-only and `LOCKED_UNCONSUMED`.

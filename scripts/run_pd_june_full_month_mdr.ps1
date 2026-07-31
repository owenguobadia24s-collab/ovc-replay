[CmdletBinding()]
param(
    [ValidateSet("profile", "plan", "preflight", "execute")]
    [string]$Command = "profile"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvPython = Join-Path $repositoryRoot ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    $python = $venvPython
}
else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCommand) {
        throw "Python was not found. Create .venv or install Python 3.11 or newer."
    }
    $python = $pythonCommand.Source
}

Write-Host "Programme: PD-JUNE-FULL-MONTH-MDR"
Write-Host "Plan amendments: PD-JUNE-FM-A1-JULY-NATIVE-H1-WAIVER; PD-JUNE-FM-A2-PAIRED-SPARSE-M1-ACCEPTANCE"
Write-Host "Target: 2026-06-01T00:00:00Z through 2026-07-01T00:00:00Z (end exclusive)"
Write-Host "Context source: 2026-05-30T00:00:00Z through 2026-07-03T00:00:00Z (end exclusive)"
Write-Host "May and July eligibility: CONTEXT_ONLY"
Write-Host "Native July H1: WAIVED_BY_OPERATOR_A1_PROVIDER_OBJECT_UNAVAILABLE"
Write-Host "Sparse M1 policy: EXACT BID/ASK PAIRING; ABSENCES RECORDED; NO REPAIR"
Write-Host "Incomplete derived buckets: NOT_EVALUABLE / CENSORED; NO BRIDGING"
Write-Host "Provider execution in CI: DENIED"

$env:PYTHONPATH = (Join-Path $repositoryRoot "src")

if ($Command -in @("preflight", "execute")) {
    if ([string]::IsNullOrWhiteSpace($env:OVC_EXTERNAL_ARTIFACT_ROOT)) {
        throw "OVC_EXTERNAL_ARTIFACT_ROOT is required for $Command."
    }
    Write-Host "External artifact root: $env:OVC_EXTERNAL_ARTIFACT_ROOT"
}

$arguments = @(
    "-m",
    "ovc.research_operations.prospective_source.dukascopy_full_month_mdr_a2",
    $Command,
    "--repository-root",
    $repositoryRoot
)

if ($Command -eq "execute") {
    $arguments += @(
        "--gate",
        "PD-JUNE-FM-G1",
        "--amendment-gate",
        "PD-JUNE-FM-A2-PAIRED-SPARSE-M1-ACCEPTANCE"
    )
    Write-Host "Operator approval binding: PD-JUNE-FM-G1"
    Write-Host "A2 operator approval binding: PD-JUNE-FM-A2-PAIRED-SPARSE-M1-ACCEPTANCE"
    Write-Host "Provider execution location: OPERATOR_LOCAL_ONLY"
}

& $python @arguments
exit $LASTEXITCODE

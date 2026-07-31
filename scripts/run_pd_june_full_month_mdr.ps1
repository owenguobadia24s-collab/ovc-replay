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
Write-Host "Target: 2026-06-01T00:00:00Z through 2026-07-01T00:00:00Z (end exclusive)"
Write-Host "Context source: 2026-05-30T00:00:00Z through 2026-07-03T00:00:00Z (end exclusive)"
Write-Host "May and July eligibility: CONTEXT_ONLY"
Write-Host "Provider execution in CI: DENIED"

$env:PYTHONPATH = (Join-Path $repositoryRoot "src")

if ($Command -eq "profile") {
    & $python -m ovc.research_operations.pattern_discovery.full_month_mdr profile
    exit $LASTEXITCODE
}

if ($Command -in @("preflight", "execute")) {
    if ([string]::IsNullOrWhiteSpace($env:OVC_EXTERNAL_ARTIFACT_ROOT)) {
        throw "OVC_EXTERNAL_ARTIFACT_ROOT is required for $Command."
    }
    Write-Host "External artifact root: $env:OVC_EXTERNAL_ARTIFACT_ROOT"
}

$arguments = @(
    "-m",
    "ovc.research_operations.prospective_source.dukascopy_full_month_mdr",
    $Command,
    "--repository-root",
    $repositoryRoot
)

if ($Command -eq "execute") {
    $arguments += @("--gate", "PD-JUNE-FM-G1")
    Write-Host "Operator approval binding: PD-JUNE-FM-G1"
    Write-Host "Provider execution location: OPERATOR_LOCAL_ONLY"
}

& $python @arguments
exit $LASTEXITCODE

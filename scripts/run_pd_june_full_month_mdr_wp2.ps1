[CmdletBinding()]
param(
    [ValidateSet("preflight", "execute")]
    [string]$Command = "preflight"
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

if ([string]::IsNullOrWhiteSpace($env:OVC_EXTERNAL_ARTIFACT_ROOT)) {
    throw "OVC_EXTERNAL_ARTIFACT_ROOT is required for PD-JUNE-FM-WP2 $Command."
}

Write-Host "Programme: PD-JUNE-FULL-MONTH-MDR"
Write-Host "Packet: PD-JUNE-FM-WP2"
Write-Host "Source slice: RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1"
Write-Host "Target: 2026-06-01T00:00:00Z through 2026-07-01T00:00:00Z (end exclusive)"
Write-Host "Source context: 2026-05-30T00:00:00Z through 2026-07-03T00:00:00Z (end exclusive)"
Write-Host "Provider execution: NONE"
Write-Host "Replay execution in CI: DENIED"
Write-Host "External artifact root: $env:OVC_EXTERNAL_ARTIFACT_ROOT"

$env:PYTHONPATH = (Join-Path $repositoryRoot "src")
$arguments = @(
    "-m",
    "ovc.research_operations.prospective_source.full_month_mdr_replay",
    $Command,
    "--repository-root",
    $repositoryRoot
)

if ($Command -eq "execute") {
    $arguments += @("--gate", "PD-JUNE-FM-G1")
    Write-Host "Delegated authority binding: PD-JUNE-FM-G1"
    Write-Host "Execution location: OPERATOR_LOCAL_ONLY"
    Write-Host "Output class: NOT_A_RELEASE / SELECTOR_NONE / R2_DENIED / VALIDATION_DENIED"
}

& $python @arguments
exit $LASTEXITCODE

[CmdletBinding()]
param(
    [ValidateSet("profile")]
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
Write-Host "Provider execution in this packet: NONE"
Write-Host "Provider execution in CI: DENIED"

$arguments = @(
    "-m",
    "ovc.research_operations.pattern_discovery.full_month_mdr",
    $Command
)

$env:PYTHONPATH = (Join-Path $repositoryRoot "src")
& $python @arguments
exit $LASTEXITCODE

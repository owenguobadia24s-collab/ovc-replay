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
    throw "OVC_EXTERNAL_ARTIFACT_ROOT is not set for this PowerShell process."
}

$arguments = @(
    "-m",
    "ovc.research_operations.prospective_source.dukascopy_intake",
    $Command,
    "--repository-root",
    $repositoryRoot
)

if ($Command -eq "execute") {
    $arguments += @("--gate", "RPS-G1")
}

Write-Host "RPS-WP2 command: $Command"
Write-Host "Repository: $repositoryRoot"
Write-Host "External artifact root: $env:OVC_EXTERNAL_ARTIFACT_ROOT"

& $python @arguments
exit $LASTEXITCODE

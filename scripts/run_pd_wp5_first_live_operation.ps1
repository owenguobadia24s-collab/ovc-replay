[CmdletBinding()]
param(
    [ValidateSet("preflight")]
    [string]$Command = "preflight",

    [string]$CandidatePackage
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

$arguments = @(
    "-m",
    "ovc.research_operations.pattern_discovery.first_live_operation",
    $Command,
    "--repository-root",
    $repositoryRoot
)

if (-not [string]::IsNullOrWhiteSpace($CandidatePackage)) {
    $resolvedPackage = (Resolve-Path $CandidatePackage).Path
    $arguments += @("--candidate-package", $resolvedPackage)
}

Write-Host "PD-WP5 first LIVE_PROSPECTIVE operation: $Command"
Write-Host "Activation merge: aa29b23a7a83e33880ac2d80deb013f0c0390f30"
Write-Host "Source binding: RPS.BINDING.32fb3003efa072916c11e907"
Write-Host "Signing binding: RPS.SIGNING.50092c28981fef08f53a6cb5"
Write-Host "Operation limit: 1"
Write-Host "Replay backfill: denied"
Write-Host "Provider network access: none"
Write-Host "Repository: $repositoryRoot"

& $python @arguments
exit $LASTEXITCODE

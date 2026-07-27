[CmdletBinding()]
param(
    [ValidateSet("preflight", "setup-key", "accept-replay")]
    [string]$Command = "preflight",

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^OVC\.OPERATOR\.[A-Za-z0-9_.-]+\.[Vv][0-9]+$')]
    [string]$OperatorId,

    [switch]$ConfirmPrivateKeyProtected
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

$sshKeygen = Get-Command ssh-keygen -ErrorAction SilentlyContinue
if ($null -eq $sshKeygen) {
    throw "OpenSSH ssh-keygen is required. Enable the Windows OpenSSH Client feature."
}

$normalizedOperatorId = $OperatorId.ToUpperInvariant()
$arguments = @(
    "-m",
    "ovc.research_operations.prospective_source.operator_replay_acceptance",
    $Command,
    "--repository-root",
    $repositoryRoot,
    "--operator-id",
    $normalizedOperatorId
)

if ($Command -in @("setup-key", "accept-replay")) {
    $arguments += @("--gate", "RPS-G3")
}

if ($Command -eq "accept-replay") {
    if (-not $ConfirmPrivateKeyProtected) {
        throw "accept-replay requires -ConfirmPrivateKeyProtected after applying restrictive OS permissions to the private key."
    }
    $arguments += "--confirm-private-key-protected"
}

Write-Host "RPS-WP4 operator signing/replay command: $Command"
Write-Host "Authority gate: RPS-G3"
Write-Host "Operator: $normalizedOperatorId"
Write-Host "Run: RPS.RUN.7aeb551335d766ee3bf503e6"
Write-Host "Binding: RPS.BINDING.32fb3003efa072916c11e907"
Write-Host "Operation mode: TIME_GATED_REPLAY"
Write-Host "ACTIVE_RESEARCH_TRIAGE: false"
Write-Host "LIVE_PROSPECTIVE append: denied"
Write-Host "Write authority: false"
Write-Host "Repository: $repositoryRoot"
Write-Host "External artifact root: $env:OVC_EXTERNAL_ARTIFACT_ROOT"

& $python @arguments
exit $LASTEXITCODE

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArgs
)

$ErrorActionPreference = "Stop"
$RepoRoot = if ($env:OVC_REPOSITORY_ROOT) { $env:OVC_REPOSITORY_ROOT } else { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
$SrcRoot = Join-Path $RepoRoot "src"

if (-not (Test-Path $SrcRoot -PathType Container)) {
    throw "OVC src directory not found: $SrcRoot"
}

$env:OVC_REPOSITORY_ROOT = $RepoRoot
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$SrcRoot;$env:PYTHONPATH" } else { $SrcRoot }

& python -m ovc @CommandArgs
exit $LASTEXITCODE

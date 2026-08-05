[CmdletBinding()]
param(
    [string]$ReplayRoot,
    [string]$Output,
    [string]$LegacyBenchmarkManifest
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $env:OVC_EXTERNAL_ARTIFACT_ROOT) {
    throw "OVC_EXTERNAL_ARTIFACT_ROOT is required."
}

if (-not $ReplayRoot) {
    $ReplayRoot = Join-Path $env:OVC_EXTERNAL_ARTIFACT_ROOT `
        "c2-anatomy-redesign-v0-2\wp10-rules\june-vnext-full-replay"
}
if (-not $Output) {
    $Output = Join-Path $ReplayRoot `
        "disposition-evidence\CEAR_G10_DISPOSITION_EVIDENCE.json"
}

if (-not (Test-Path -LiteralPath $ReplayRoot -PathType Container)) {
    throw "Completed replay root is unavailable: $ReplayRoot"
}

$required = @(
    "orchestration-receipt.json",
    "determinism-receipt.json",
    "restart-receipt.json",
    "run-001\output-manifest.json",
    "run-002\output-manifest.json",
    "restart-verification\output-manifest.json"
)
foreach ($relative in $required) {
    $path = Join-Path $ReplayRoot $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required replay evidence is unavailable: $path"
    }
}

$arguments = @(
    "-m", "ovc.opt_b.c2_vnext.disposition_evidence",
    "--replay-root", $ReplayRoot,
    "--repository-root", (Get-Location).Path,
    "--output", $Output
)
if ($LegacyBenchmarkManifest) {
    if (-not (Test-Path -LiteralPath $LegacyBenchmarkManifest -PathType Leaf)) {
        throw "Legacy benchmark manifest is unavailable: $LegacyBenchmarkManifest"
    }
    $arguments += @("--legacy-benchmark-manifest", $LegacyBenchmarkManifest)
}

$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = if ($previousPythonPath) { "src;$previousPythonPath" } else { "src" }
    & python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "CEAR-G10 disposition-evidence construction failed with exit code $LASTEXITCODE."
    }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}

if (-not (Test-Path -LiteralPath $Output -PathType Leaf)) {
    throw "Expected compact evidence was not written: $Output"
}

Write-Host "CEAR-G10 compact disposition evidence: $Output"

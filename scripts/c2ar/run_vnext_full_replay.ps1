[CmdletBinding()]
param(
    [ValidateSet("build-binding", "preflight", "execute")]
    [string]$Command = "preflight",
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$ExternalRoot = $env:OVC_EXTERNAL_ARTIFACT_ROOT,
    [string]$ExpectedMainBaseline = "8ff30900da9af11a2defe612fa6b1f0e86fb7a5f",
    [string]$BindingPath,
    [string]$OutputRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ExternalRoot)) {
    throw "OVC_EXTERNAL_ARTIFACT_ROOT or -ExternalRoot is required."
}
if ([string]::IsNullOrWhiteSpace($BindingPath)) {
    $BindingPath = Join-Path $ExternalRoot "c2-anatomy-redesign-v0-2\source-bindings\C2_VNEXT_FULL_REPLAY_INPUT_BINDING_v1.json"
}
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $ExternalRoot "c2-anatomy-redesign-v0-2\wp10-rules\june-vnext-full-replay"
}

$venvPython = Join-Path $RepositoryRoot ".venv\Scripts\python.exe"
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

Set-Location $RepositoryRoot
$env:PYTHONPATH = Join-Path $RepositoryRoot "src"
$env:OVC_EXTERNAL_ARTIFACT_ROOT = $ExternalRoot

if ($Command -eq "build-binding") {
    New-Item -ItemType Directory -Force -Path (Split-Path $BindingPath) | Out-Null
    & $python -m ovc.opt_b.c2_vnext.full_replay build-binding `
        --repository-root $RepositoryRoot `
        --external-root $ExternalRoot `
        --output $BindingPath `
        --expected-main-baseline $ExpectedMainBaseline
    exit $LASTEXITCODE
}

if (-not (Test-Path $BindingPath)) {
    throw "Missing full-replay input-binding record: $BindingPath. Run this script with -Command build-binding first."
}

$binding = Get-Content -Raw -Path $BindingPath | ConvertFrom-Json
$expectedCodeCommit = [string]$binding.code.expected_code_commit
$actualHead = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to resolve repository HEAD."
}
if ($actualHead -ne $expectedCodeCommit) {
    throw "Code-head mismatch. Binding expects $expectedCodeCommit; found $actualHead. Rebuild the binding on the intended immutable commit."
}
$dirtyPaths = @(git status --porcelain)
if ($dirtyPaths.Count -ne 0) {
    throw "The repository worktree is not clean. Preserve local work and use a clean git worktree before replay."
}

if ($Command -eq "preflight") {
    & $python -m ovc.opt_b.c2_vnext.full_replay preflight `
        --repository-root $RepositoryRoot `
        --input-binding $BindingPath `
        --expected-code-commit $expectedCodeCommit
    exit $LASTEXITCODE
}

if (Test-Path $OutputRoot) {
    throw "Output root already exists: $OutputRoot. Use a new path for every full orchestration."
}

& $python -m ovc.opt_b.c2_vnext.full_replay orchestrate `
    --repository-root $RepositoryRoot `
    --input-binding $BindingPath `
    --output-root $OutputRoot `
    --expected-main-baseline $ExpectedMainBaseline `
    --expected-code-commit $expectedCodeCommit `
    --instrument GBPUSD `
    --source-slice-id "RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1" `
    --source-manifest-sha256 "1578b555f3d5aa2822b603141261f86a047096030e5faacd4380ef2c6d4f52e3" `
    --integrated-freeze-id "C2AR.INTEGRATED.SHADOW.FREEZE.v1" `
    --integrated-freeze-sha256 "856b2602bc52764974009dd2d5fdf5259db74242c6732a5a3b42905eb06c0a7f" `
    --context-start-utc "2026-05-30T00:00:00Z" `
    --target-start-utc "2026-06-01T00:00:00Z" `
    --target-end-exclusive-utc "2026-07-01T00:00:00Z" `
    --context-end-exclusive-utc "2026-07-03T00:00:00Z" `
    --clock 15M `
    --clock 2H_A_L `
    --side BID `
    --side ASK `
    --population-scope COMPLETE_REGISTERED_LAWFUL_DISCOVERY_POPULATION `
    --clean-run-count 2 `
    --workspace-policy FRESH_PER_RUN `
    --checkpoint-policy FROM_INPUT_BINDING `
    --capacity-policy FROM_INPUT_BINDING `
    --resume-enabled `
    --require-readable-payloads `
    --require-complete-accounting `
    --require-first-valid-chronology `
    --require-identical-logical-hashes `
    --emit-input-manifest `
    --emit-output-manifest `
    --emit-population-reconciliation `
    --emit-denominator-reconciliation `
    --emit-capacity-receipt `
    --emit-checkpoint-receipt `
    --emit-restart-receipt `
    --emit-determinism-comparison `
    --deny-outcome-inputs `
    --deny-validation-inputs `
    --deny-legacy-upstream-influence `
    --deny-selector-write `
    --deny-release-publication `
    --deny-r2-write

exit $LASTEXITCODE

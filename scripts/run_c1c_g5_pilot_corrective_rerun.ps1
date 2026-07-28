[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('preflight', 'execute', 'finalize')]
    [string]$Command = 'preflight',

    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,

    [string]$Gate = 'C1C-G5',

    [string]$PilotRunId,

    [string]$ReviewFile
)

$ErrorActionPreference = 'Stop'

$python = Join-Path $RepositoryRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $python = (Get-Command python -ErrorAction Stop).Source
}

$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $RepositoryRoot 'src'
    $arguments = @(
        '-m',
        'ovc.research_operations.pattern_discovery.pilot_corrective_rerun',
        $Command,
        '--repository-root',
        $RepositoryRoot
    )

    if ($Gate) {
        $arguments += @('--gate', $Gate)
    }
    if ($PilotRunId) {
        $arguments += @('--pilot-run-id', $PilotRunId)
    }
    if ($ReviewFile) {
        $arguments += @('--review-file', $ReviewFile)
    }

    & $python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "C1C-G5 corrective Pilot Discovery command failed with exit code $LASTEXITCODE."
    }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}

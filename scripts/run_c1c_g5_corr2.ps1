[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('preflight', 'prepare', 'finalize')]
    [string]$Command = 'preflight',

    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,

    [string]$PilotRunId = 'PD.PILOT.RUN.96c16f11717e787f971851ee',

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
        'ovc.research_operations.pattern_discovery.review_findings_corr2',
        $Command,
        '--repository-root',
        $RepositoryRoot,
        '--pilot-run-id',
        $PilotRunId
    )

    if ($ReviewFile) {
        $arguments += @('--review-file', $ReviewFile)
    }

    & $python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "C1C-G5 CORR2 command failed with exit code $LASTEXITCODE."
    }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}

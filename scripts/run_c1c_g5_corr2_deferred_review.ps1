[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('preflight', 'prepare', 'finalize')]
    [string]$Command = 'preflight',

    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,

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
        'ovc.research_operations.pattern_discovery.pilot_corr2_review_closure_entry',
        $Command,
        '--repository-root',
        $RepositoryRoot
    )

    if ($Command -eq 'finalize') {
        if (-not $ReviewFile) {
            throw 'finalize requires -ReviewFile <completed-corr2-review.json>.'
        }
        $arguments += @('--review-file', $ReviewFile)
    }

    & $python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "C1C-G5-CORR2 command failed with exit code $LASTEXITCODE."
    }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}

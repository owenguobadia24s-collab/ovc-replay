param(
    [string]$RepositoryRoot = (Resolve-Path "$PSScriptRoot\.."),
    [string]$SourceCommit = $env:OVC_SOURCE_COMMIT
)

$ErrorActionPreference = "Stop"
if (-not $SourceCommit) {
    throw "Set OVC_SOURCE_COMMIT to the exact repository commit represented by the read model."
}

$env:PYTHONPATH = Join-Path $RepositoryRoot "src"
$readModel = Join-Path $RepositoryRoot "var\research_operations\read_model\current.json"
python (Join-Path $RepositoryRoot "scripts\build_research_read_model.py") --source-commit $SourceCommit --output $readModel
if ($LASTEXITCODE -ne 0) { throw "Read-model build failed." }

$env:OVC_RESEARCH_READ_MODEL = $readModel
python -m streamlit run (Join-Path $RepositoryRoot "apps\research_console\Home.py") --server.address 127.0.0.1

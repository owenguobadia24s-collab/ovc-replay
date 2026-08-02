#requires -Version 7.0
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Repository = "owenguobadia24s-collab/ovc-replay",
    [string]$WorkPacketPath = "fixtures/development/receipt_bot/work_packet_shadow_v0_1.json",
    [string]$TargetContentPath = "fixtures/development/receipt_bot/shadow_receipt_payload_v0_1.json",
    [Parameter(Mandatory = $true)]
    [string]$RulesetEvidencePath,
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function ConvertTo-Base64Url {
    param([byte[]]$Bytes)
    [Convert]::ToBase64String($Bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function ConvertTo-JsonBytes {
    param([hashtable]$Value)
    [Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Compress -Depth 20))
}

function Get-GitHubAppJwt {
    param(
        [int64]$AppId,
        [string]$PrivateKeyPath
    )
    if (-not (Test-Path -LiteralPath $PrivateKeyPath -PathType Leaf)) {
        throw "GitHub App private key not found."
    }
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $header = ConvertTo-Base64Url (ConvertTo-JsonBytes @{ alg = "RS256"; typ = "JWT" })
    $payload = ConvertTo-Base64Url (ConvertTo-JsonBytes @{ iat = $now - 60; exp = $now + 540; iss = $AppId })
    $unsigned = "$header.$payload"
    $rsa = [Security.Cryptography.RSA]::Create()
    try {
        $pem = Get-Content -LiteralPath $PrivateKeyPath -Raw
        $rsa.ImportFromPem($pem)
        $signature = $rsa.SignData(
            [Text.Encoding]::UTF8.GetBytes($unsigned),
            [Security.Cryptography.HashAlgorithmName]::SHA256,
            [Security.Cryptography.RSASignaturePadding]::Pkcs1
        )
    }
    finally {
        $rsa.Dispose()
    }
    "$unsigned.$(ConvertTo-Base64Url $signature)"
}

function Get-EncodedRepoPath {
    param([string]$Path)
    (($Path -split '/') | ForEach-Object { [Uri]::EscapeDataString($_) }) -join '/'
}

function Assert-ExternalRulesetEvidence {
    param([object]$Ruleset)
    if ($Ruleset.enforcement -ne "active") {
        throw "Ruleset evidence is not active."
    }
    $bypass = @($Ruleset.bypass_actors)
    if ($bypass.Count -ne 0) {
        throw "Ruleset contains bypass actors."
    }
    $includes = @($Ruleset.conditions.ref_name.include)
    if (($includes -notcontains "refs/heads/main") -and ($includes -notcontains "~DEFAULT_BRANCH")) {
        throw "Ruleset does not target main/default branch."
    }
    $types = @($Ruleset.rules | ForEach-Object { $_.type })
    foreach ($required in @("pull_request", "deletion", "non_fast_forward", "required_status_checks")) {
        if ($types -notcontains $required) {
            throw "Ruleset is missing required rule type: $required"
        }
    }
}

function Invoke-GitHubApi {
    param(
        [ValidateSet("GET", "POST", "PUT")]
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers,
        [object]$Body
    )
    $params = @{
        Method = $Method
        Uri = $Uri
        Headers = $Headers
        ErrorAction = "Stop"
    }
    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Compress -Depth 30)
    }
    Invoke-RestMethod @params
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$workPacketFile = (Resolve-Path (Join-Path $repoRoot $WorkPacketPath)).Path
$targetContentFile = (Resolve-Path (Join-Path $repoRoot $TargetContentPath)).Path
$rulesetFile = (Resolve-Path $RulesetEvidencePath).Path

if (-not $OutputDirectory) {
    if (-not $env:OVC_EXTERNAL_ARTIFACT_ROOT) {
        throw "Set OVC_EXTERNAL_ARTIFACT_ROOT or provide -OutputDirectory."
    }
    $OutputDirectory = Join-Path $env:OVC_EXTERNAL_ARTIFACT_ROOT "governance/DA-G4B/shadow-001"
}
$repoRootPrefix = $repoRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
$outputFull = [IO.Path]::GetFullPath($OutputDirectory)
if ($outputFull.StartsWith($repoRootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Shadow audit output must remain outside the repository."
}
New-Item -ItemType Directory -Force -Path $outputFull | Out-Null

foreach ($name in @(
    "OVC_RECEIPT_BOT_APP_ID",
    "OVC_RECEIPT_BOT_INSTALLATION_ID",
    "OVC_RECEIPT_BOT_APP_SLUG",
    "OVC_RECEIPT_BOT_PRIVATE_KEY_PATH"
)) {
    if (-not (Get-Item "env:$name" -ErrorAction SilentlyContinue).Value) {
        throw "Missing required process environment variable: $name"
    }
}

$appId = [int64]$env:OVC_RECEIPT_BOT_APP_ID
$installationId = [int64]$env:OVC_RECEIPT_BOT_INSTALLATION_ID
$appSlug = $env:OVC_RECEIPT_BOT_APP_SLUG
$privateKeyPath = $env:OVC_RECEIPT_BOT_PRIVATE_KEY_PATH
$packet = Get-Content -LiteralPath $workPacketFile -Raw | ConvertFrom-Json -Depth 30
$ruleset = Get-Content -LiteralPath $rulesetFile -Raw | ConvertFrom-Json -Depth 30
Assert-ExternalRulesetEvidence $ruleset

if ($packet.branch -notlike "bot/ovc-dev-accel-receipts/da-g4b-shadow-*") {
    throw "Work packet branch is outside the dedicated DA-G4B shadow namespace."
}
if ($packet.pull_request_title -notmatch "(?i)DA-G4B" -or $packet.pull_request_title -notmatch "(?i)shadow") {
    throw "Work packet PR title must identify DA-G4B and shadow status."
}
if (@($packet.target_files).Count -ne 1) {
    throw "The pre-activation shadow must contain exactly one target file."
}
$target = $packet.target_files[0]
if ($target.path -notlike "docs/releases/development-acceleration-v0-1/da-wp4b-shadow/*.json") {
    throw "Shadow target path is outside the dedicated allowlist."
}
$targetHash = (Get-FileHash -LiteralPath $targetContentFile -Algorithm SHA256).Hash.ToLowerInvariant()
if ($targetHash -ne $target.content_sha256) {
    throw "Target content SHA-256 does not match the frozen work packet."
}
$rulesetHash = (Get-FileHash -LiteralPath $rulesetFile -Algorithm SHA256).Hash.ToLowerInvariant()

$api = "https://api.github.com"
$appJwt = Get-GitHubAppJwt -AppId $appId -PrivateKeyPath $privateKeyPath
$appHeaders = @{
    Authorization = "Bearer $appJwt"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "ovc-da-g4b-shadow"
}
$tokenResponse = Invoke-GitHubApi -Method POST -Uri "$api/app/installations/$installationId/access_tokens" -Headers $appHeaders -Body @{}
$installationToken = $tokenResponse.token
if (-not $installationToken) {
    throw "GitHub did not return an installation token."
}
try {
    $permissionNames = @($tokenResponse.permissions.PSObject.Properties.Name)
    foreach ($name in $permissionNames) {
        if ($name -notin @("contents", "pull_requests", "metadata")) {
            throw "Installation token exposes an undeclared permission: $name"
        }
    }
    if ($tokenResponse.permissions.contents -ne "write") {
        throw "Installation token does not have exact Contents: write permission."
    }
    if ($tokenResponse.permissions.pull_requests -ne "write") {
        throw "Installation token does not have exact Pull requests: write permission."
    }

    $headers = @{
        Authorization = "Bearer $installationToken"
        Accept = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
        "User-Agent" = "ovc-da-g4b-shadow"
    }
    $mainRef = Invoke-GitHubApi -Method GET -Uri "$api/repos/$Repository/git/ref/heads/main" -Headers $headers -Body $null
    $currentMainSha = $mainRef.object.sha
    if ($packet.source_main_sha -ne $packet.current_main_sha -or $packet.source_main_sha -ne $currentMainSha) {
        throw "STALE_MAIN_SHA: regenerate the shadow work packet from current lawful main."
    }

    $receiptBody = Get-Content -LiteralPath $targetContentFile -Raw
    if ($receiptBody -match "ghp_|github_pat_|Bearer\s+|PRIVATE KEY") {
        throw "Target receipt contains credential-like material."
    }

    if (-not $PSCmdlet.ShouldProcess($Repository, "Create one DA-G4B shadow branch, receipt commit and unmerged PR")) {
        return
    }

    $refResponse = Invoke-GitHubApi -Method POST -Uri "$api/repos/$Repository/git/refs" -Headers $headers -Body @{
        ref = "refs/heads/$($packet.branch)"
        sha = $currentMainSha
    }
    $encodedPath = Get-EncodedRepoPath $target.path
    $contentResponse = Invoke-GitHubApi -Method PUT -Uri "$api/repos/$Repository/contents/$encodedPath" -Headers $headers -Body @{
        message = "DA-G4B shadow: add bounded receipt evidence"
        content = [Convert]::ToBase64String([IO.File]::ReadAllBytes($targetContentFile))
        branch = $packet.branch
    }
    $prResponse = Invoke-GitHubApi -Method POST -Uri "$api/repos/$Repository/pulls" -Headers $headers -Body @{
        title = $packet.pull_request_title
        head = $packet.branch
        base = "main"
        body = "DA-G4B pre-activation shadow only. Authority remains inactive. Do not merge."
        draft = $false
    }

    $audit = [ordered]@{
        schema = "ovc-receipt-bot-pre-activation-shadow-external-audit/v1"
        mode = "PRE_ACTIVATION_SHADOW"
        repository = $Repository
        app_id = $appId
        installation_id = $installationId
        app_slug = $appSlug
        credential_kind = "GITHUB_APP_INSTALLATION_TOKEN"
        revocable = $true
        operator_connector = $false
        permissions = [ordered]@{
            contents = "write"
            pull_requests = "write"
            metadata = "read"
        }
        ruleset_evidence_sha256 = $rulesetHash
        source_main_sha = $currentMainSha
        branch = $packet.branch
        target_path = $target.path
        target_content_sha256 = $targetHash
        branch_ref = $refResponse.ref
        commit_sha = $contentResponse.commit.sha
        pull_request_number = $prResponse.number
        pull_request_url = $prResponse.html_url
        authority_active = $false
        production_transport_active = $false
        merge_performed = $false
        approval_performed = $false
        force_push_performed = $false
        history_rewrite_performed = $false
        result = "PASS_CANDIDATE_PENDING_QA"
    }
    $auditPath = Join-Path $outputFull "DA_G4B_SHADOW_EXTERNAL_AUDIT.json"
    $audit | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $auditPath -Encoding utf8NoBOM
    $auditHash = (Get-FileHash -LiteralPath $auditPath -Algorithm SHA256).Hash.ToLowerInvariant()
    @{
        audit_path = $auditPath
        audit_sha256 = $auditHash
        pull_request_number = $prResponse.number
        pull_request_url = $prResponse.html_url
        authority_active = $false
    } | ConvertTo-Json -Depth 10
}
finally {
    $installationToken = $null
    $appJwt = $null
}

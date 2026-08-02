#requires -Version 7.0
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Repository = "owenguobadia24s-collab/ovc-replay",
    [Parameter(Mandatory = $true)]
    [string]$WorkPacketPath,
    [Parameter(Mandatory = $true)]
    [string]$ContentRoot,
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ExpectedProfileId = "OVC.DEVELOPMENT.ACCELERATION.RECEIPT-BOT.v0.1"
$ExpectedProfileHash = "e3e13f38dbddbf96da075c4489e2c5e7c7a03b6f42aaa9aa564e0db2813fa0f5"
$ExpectedActivationId = "4815173d1ec559164072013f20d008f2d3a5b120841e8e6cb0350ee1f1164238"
$ExpectedDecisionId = "DA-G4B.OPERATOR.PASS.20260802T163600Z"
$AllowedPaths = @(
    "docs/releases/development-acceleration-v0-1/**",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml"
)

function ConvertTo-Base64Url {
    param([byte[]]$Bytes)
    [Convert]::ToBase64String($Bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Get-GitHubAppJwt {
    param([int64]$AppId, [string]$PrivateKeyPath)
    if (-not (Test-Path -LiteralPath $PrivateKeyPath -PathType Leaf)) {
        throw "GitHub App private key not found."
    }
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $headerBytes = [Text.Encoding]::UTF8.GetBytes((@{ alg = "RS256"; typ = "JWT" } | ConvertTo-Json -Compress))
    $payloadBytes = [Text.Encoding]::UTF8.GetBytes((@{ iat = $now - 60; exp = $now + 540; iss = $AppId } | ConvertTo-Json -Compress))
    $unsigned = "$(ConvertTo-Base64Url $headerBytes).$(ConvertTo-Base64Url $payloadBytes)"
    $rsa = [Security.Cryptography.RSA]::Create()
    try {
        $rsa.ImportFromPem((Get-Content -LiteralPath $PrivateKeyPath -Raw))
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

function Invoke-GitHubApi {
    param(
        [ValidateSet("GET", "POST", "PUT", "PATCH")][string]$Method,
        [string]$Uri,
        [hashtable]$Headers,
        [object]$Body,
        [switch]$AllowNotFound
    )
    $params = @{ Method = $Method; Uri = $Uri; Headers = $Headers; ErrorAction = "Stop" }
    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Compress -Depth 30)
    }
    try {
        Invoke-RestMethod @params
    }
    catch {
        if ($AllowNotFound -and $_.Exception.Response.StatusCode.value__ -eq 404) { return $null }
        throw
    }
}

function Get-EncodedRepoPath {
    param([string]$Path)
    (($Path -split '/') | ForEach-Object { [Uri]::EscapeDataString($_) }) -join '/'
}

function Assert-SafeRelativePath {
    param([string]$Path)
    if (-not $Path -or $Path.StartsWith('/') -or $Path.Contains('\\') -or $Path -match '(^|/)\.\.(/|$)' -or $Path -match '^[A-Za-z]:') {
        throw "Unsafe target path: $Path"
    }
}

function Test-AllowedPath {
    param([string]$Path)
    if ($Path -like "docs/releases/development-acceleration-v0-1/*") { return $true }
    return $AllowedPaths -contains $Path
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$packetFile = (Resolve-Path $WorkPacketPath).Path
$contentRootFull = (Resolve-Path $ContentRoot).Path
$activeProfilePath = Join-Path $repoRoot "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_ACTIVE_PROFILE_v0_1.json"
$decisionPath = Join-Path $repoRoot "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_OPERATOR_DECISION.json"
$evaluationPath = Join-Path $repoRoot "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_ACTIVATION_EVALUATION.json"

if (-not $OutputDirectory) {
    if (-not $env:OVC_EXTERNAL_ARTIFACT_ROOT) { throw "Set OVC_EXTERNAL_ARTIFACT_ROOT or provide -OutputDirectory." }
    $OutputDirectory = Join-Path $env:OVC_EXTERNAL_ARTIFACT_ROOT "governance/receipt-bot"
}
$outputFull = [IO.Path]::GetFullPath($OutputDirectory)
$repoPrefix = $repoRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
if ($outputFull.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Receipt-bot audit output must remain outside the repository."
}
New-Item -ItemType Directory -Force -Path $outputFull | Out-Null

foreach ($name in @("OVC_RECEIPT_BOT_APP_ID", "OVC_RECEIPT_BOT_INSTALLATION_ID", "OVC_RECEIPT_BOT_APP_SLUG", "OVC_RECEIPT_BOT_PRIVATE_KEY_PATH")) {
    $item = Get-Item "env:$name" -ErrorAction SilentlyContinue
    if ($null -eq $item -or -not $item.Value) { throw "Missing required process environment variable: $name" }
}

$profile = Get-Content -LiteralPath $activeProfilePath -Raw | ConvertFrom-Json -Depth 30
$decision = Get-Content -LiteralPath $decisionPath -Raw | ConvertFrom-Json -Depth 30
$evaluation = Get-Content -LiteralPath $evaluationPath -Raw | ConvertFrom-Json -Depth 30
$packet = Get-Content -LiteralPath $packetFile -Raw | ConvertFrom-Json -Depth 30

if ($profile.profile_id -ne $ExpectedProfileId -or $profile.source_approved_profile_hash -ne $ExpectedProfileHash -or $profile.active -ne $true -or $profile.status -ne "ACTIVE") {
    throw "Active profile identity or status mismatch."
}
if ($profile.activation_evaluation_id -ne $ExpectedActivationId -or $evaluation.evaluation_id -ne $ExpectedActivationId -or $evaluation.status -ne "PASS" -or $evaluation.authority_active -ne $true) {
    throw "Activation evaluation is not the exact approved PASS record."
}
if ($decision.decision_id -ne $ExpectedDecisionId -or $decision.decision -ne "PASS" -or $decision.authority_active -ne $true) {
    throw "DA-G4B operator PASS is absent or mismatched."
}
if ($packet.profile_id -ne $ExpectedProfileId -or $packet.profile_hash -ne $ExpectedProfileHash) { throw "Work packet profile mismatch." }
if ($packet.programme_id -ne "OVC-DEV-ACCEL-v0.1") { throw "Work packet programme mismatch." }
if ($packet.branch -notlike "bot/ovc-dev-accel-receipts/*" -or $packet.branch -eq "main") { throw "Work packet branch is outside the active profile." }
if ($packet.source_main_sha -ne $packet.current_main_sha) { throw "STALE_MAIN_SHA in work packet." }
if ($packet.closure_status -ne "PASS" -or $packet.qa_status -ne "PASS" -or $packet.decision -ne "PASS") { throw "Work packet closure, QA and decision must all PASS." }
if ($packet.reserved_authority_delta -ne "NONE" -or @($packet.blockers).Count -ne 0 -or @($packet.warnings).Count -ne 0 -or $packet.unresolved_review_count -ne 0) {
    throw "Work packet contains an authority delta, blocker, warning or unresolved review."
}
if ($packet.rollback -match '(?i)reset --hard|force.?push|rewrite history|delete accepted') { throw "Destructive rollback is prohibited." }

$packetHash = (Get-FileHash -LiteralPath $packetFile -Algorithm SHA256).Hash.ToLowerInvariant()
$ledgerPath = Join-Path $outputFull "$($packet.idempotency_key).json"
if (Test-Path -LiteralPath $ledgerPath) {
    $prior = Get-Content -LiteralPath $ledgerPath -Raw | ConvertFrom-Json -Depth 30
    if ($prior.work_packet_sha256 -ne $packetHash) { throw "IDEMPOTENCY_COLLISION" }
    $prior | ConvertTo-Json -Depth 30
    return
}

$targets = @($packet.target_files)
if ($targets.Count -eq 0) { throw "Work packet has no target files." }
$prepared = @()
foreach ($target in $targets) {
    Assert-SafeRelativePath $target.path
    if (-not (Test-AllowedPath $target.path)) { throw "PATH_NOT_ALLOWED: $($target.path)" }
    $localPath = [IO.Path]::GetFullPath((Join-Path $contentRootFull $target.path))
    $contentPrefix = $contentRootFull.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $localPath.StartsWith($contentPrefix, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $localPath -PathType Leaf)) {
        throw "Target content is absent or escapes ContentRoot: $($target.path)"
    }
    $digest = (Get-FileHash -LiteralPath $localPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($digest -ne $target.content_sha256) { throw "Target content SHA-256 mismatch: $($target.path)" }
    $body = Get-Content -LiteralPath $localPath -Raw
    if ($body -match 'ghp_|github_pat_|Bearer\s+|PRIVATE KEY|sk-proj-') { throw "Target content contains credential-like material." }
    $prepared += [pscustomobject]@{ path = $target.path; local_path = $localPath; sha256 = $digest }
}

$appId = [int64]$env:OVC_RECEIPT_BOT_APP_ID
$installationId = [int64]$env:OVC_RECEIPT_BOT_INSTALLATION_ID
$appSlug = $env:OVC_RECEIPT_BOT_APP_SLUG
if ($appSlug -ne "ovc-dev-accel-receipt-bot") { throw "Unexpected GitHub App slug." }
$appJwt = Get-GitHubAppJwt -AppId $appId -PrivateKeyPath $env:OVC_RECEIPT_BOT_PRIVATE_KEY_PATH
$api = "https://api.github.com"
$appHeaders = @{ Authorization = "Bearer $appJwt"; Accept = "application/vnd.github+json"; "X-GitHub-Api-Version" = "2022-11-28"; "User-Agent" = "ovc-da-receipt-bot" }
$tokenResponse = Invoke-GitHubApi -Method POST -Uri "$api/app/installations/$installationId/access_tokens" -Headers $appHeaders -Body @{}
$installationToken = $tokenResponse.token
if (-not $installationToken) { throw "GitHub did not return an installation token." }
try {
    $permissionNames = @($tokenResponse.permissions.PSObject.Properties.Name)
    foreach ($name in $permissionNames) {
        if ($name -notin @("contents", "pull_requests", "metadata")) { throw "Installation token exposes an undeclared permission: $name" }
    }
    if ($tokenResponse.permissions.contents -ne "write" -or $tokenResponse.permissions.pull_requests -ne "write") { throw "Installation token permissions do not match the approved profile." }
    $headers = @{ Authorization = "Bearer $installationToken"; Accept = "application/vnd.github+json"; "X-GitHub-Api-Version" = "2022-11-28"; "User-Agent" = "ovc-da-receipt-bot" }
    $mainRef = Invoke-GitHubApi -Method GET -Uri "$api/repos/$Repository/git/ref/heads/main" -Headers $headers -Body $null
    if ($mainRef.object.sha -ne $packet.source_main_sha) { throw "STALE_MAIN_SHA: current main differs from the frozen work packet." }

    if (-not $PSCmdlet.ShouldProcess($Repository, "Create or update one bounded receipt proposal branch and pull request")) { return }

    $branchRef = Invoke-GitHubApi -Method GET -Uri "$api/repos/$Repository/git/ref/heads/$($packet.branch)" -Headers $headers -Body $null -AllowNotFound
    if ($null -eq $branchRef) {
        $branchRef = Invoke-GitHubApi -Method POST -Uri "$api/repos/$Repository/git/refs" -Headers $headers -Body @{ ref = "refs/heads/$($packet.branch)"; sha = $packet.source_main_sha }
    }
    elseif ($branchRef.object.sha -ne $packet.source_main_sha) {
        throw "Existing bot branch is not pinned to the frozen source main SHA."
    }

    $written = @()
    foreach ($target in $prepared) {
        $encoded = Get-EncodedRepoPath $target.path
        $existing = Invoke-GitHubApi -Method GET -Uri "$api/repos/$Repository/contents/$encoded?ref=$([Uri]::EscapeDataString($packet.branch))" -Headers $headers -Body $null -AllowNotFound
        $putBody = @{ message = "DA receipt: $($packet.packet_id)"; content = [Convert]::ToBase64String([IO.File]::ReadAllBytes($target.local_path)); branch = $packet.branch }
        if ($null -ne $existing) {
            $existingBytes = [Convert]::FromBase64String(($existing.content -replace '\s', ''))
            $existingHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($existingBytes)).ToLowerInvariant()
            if ($existingHash -eq $target.sha256) {
                $written += @{ path = $target.path; content_sha256 = $target.sha256; result = "IDEMPOTENT_REUSE" }
                continue
            }
            $putBody.sha = $existing.sha
        }
        $response = Invoke-GitHubApi -Method PUT -Uri "$api/repos/$Repository/contents/$encoded" -Headers $headers -Body $putBody
        $written += @{ path = $target.path; content_sha256 = $target.sha256; commit_sha = $response.commit.sha; result = "WRITTEN" }
    }

    $owner = $Repository.Split('/')[0]
    $headQuery = [Uri]::EscapeDataString("$owner`:$($packet.branch)")
    $prs = @(Invoke-GitHubApi -Method GET -Uri "$api/repos/$Repository/pulls?state=open&head=$headQuery&base=main" -Headers $headers -Body $null)
    if ($prs.Count -gt 1) { throw "More than one open PR exists for the bounded bot branch." }
    if ($prs.Count -eq 0) {
        $pr = Invoke-GitHubApi -Method POST -Uri "$api/repos/$Repository/pulls" -Headers $headers -Body @{ title = $packet.pull_request_title; head = $packet.branch; base = "main"; body = "Bounded Development Acceleration receipt proposal. Bot merge and approval authority are permanently denied."; draft = $false }
    }
    else {
        $pr = Invoke-GitHubApi -Method PATCH -Uri "$api/repos/$Repository/pulls/$($prs[0].number)" -Headers $headers -Body @{ title = $packet.pull_request_title; body = "Bounded Development Acceleration receipt proposal. Bot merge and approval authority are permanently denied." }
    }

    $audit = [ordered]@{
        schema = "ovc-receipt-bot-production-audit/v1"
        programme_id = "OVC-DEV-ACCEL-v0.1"
        packet_id = $packet.packet_id
        idempotency_key = $packet.idempotency_key
        work_packet_sha256 = $packetHash
        source_main_sha = $packet.source_main_sha
        branch = $packet.branch
        pull_request_number = $pr.number
        pull_request_url = $pr.html_url
        app_slug = $appSlug
        app_id = $appId
        installation_id = $installationId
        credential_kind = "GITHUB_APP_INSTALLATION_TOKEN"
        credential_persisted = $false
        files = $written
        authority_active = $true
        merge_performed = $false
        approval_performed = $false
        force_push_performed = $false
        history_rewrite_performed = $false
        result = "PASS"
    }
    $audit | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $ledgerPath -Encoding utf8NoBOM
    $audit | ConvertTo-Json -Depth 30
}
finally {
    $installationToken = $null
    $appJwt = $null
}

# RPS-WP4 — Windows Operator Guide

## Scope

This command registers one operator-local Ed25519 signing-binding candidate and signs the exact accepted `TIME_GATED_REPLAY` run:

- source slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`;
- compute run: `RPS.RUN.7aeb551335d766ee3bf503e6`;
- source binding: `RPS.BINDING.32fb3003efa072916c11e907`;
- RPS-G3 merge: `c8429ebdf8774a876d5a33e495cb313e31c8d034`.

It does not activate research triage, enable LIVE_PROSPECTIVE append or grant write authority.

## Prerequisites

- Windows PowerShell;
- Python 3.11 or newer, preferably the repository `.venv`;
- Windows OpenSSH Client with `ssh-keygen` available;
- the exact accepted source and compute run under `OVC_EXTERNAL_ARTIFACT_ROOT`;
- repository on clean `main` at the latest lawful tip;
- one explicit operator ID matching `OVC.OPERATOR.<UPPERCASE_ID>.V<NUMBER>`.

Recommended sole-operator identity for this local environment:

`OVC.OPERATOR.PRIMARY.LOCAL.V1`

This is a governed identifier, not an email address or Windows username.

## Prepare repository and environment

```powershell
cd C:\Users\Owner\OVIS\ovc-replay
git switch main
git pull --ff-only
git status --short

$env:OVC_EXTERNAL_ARTIFACT_ROOT = `
    "C:\Users\Owner\OVIS\ovc-replay-external-artifacts"

$operatorId = "OVC.OPERATOR.PRIMARY.LOCAL.V1"
```

`git status --short` must show no tracked change.

## 1. Preflight

```powershell
.\scripts\run_rps_wp4_operator_replay_acceptance.ps1 `
    -Command preflight `
    -OperatorId $operatorId
```

Expected status:

`READY_FOR_OPERATOR_SIGNING_AND_TIME_GATED_REPLAY_ACCEPTANCE`

Preflight re-verifies all five compact compute files and all 21 manifest-declared derived payload files. It also confirms the accepted RPS-G3 state and OpenSSH availability.

## 2. Generate the operator key

```powershell
.\scripts\run_rps_wp4_operator_replay_acceptance.ps1 `
    -Command setup-key `
    -OperatorId $operatorId
```

Expected status:

`KEY_CREATED_AWAITING_PRIVATE_KEY_PROTECTION_CONFIRMATION`

The key is created outside Git under the external artifact root. The command refuses to overwrite an existing key.

The private key must never be uploaded, pasted into chat, committed, emailed or copied into the repository.

## 3. Apply restrictive Windows permissions

For `OVC.OPERATOR.PRIMARY.LOCAL.V1`, the key path is:

```powershell
$key = Join-Path $env:OVC_EXTERNAL_ARTIFACT_ROOT `
    "prospective-source\operator-signing\ovc-operator-primary-local-v1\id_ed25519"

$principal = "$env:USERDOMAIN\$env:USERNAME"
icacls $key /inheritance:r
icacls $key /grant:r "${principal}:(F)"
icacls $key
```

Review the final `icacls` output. Only the intended operator account and unavoidable Windows system/administrator principals should retain access according to the operator's local security policy.

The repository does not claim to prove Windows ACL correctness. `-ConfirmPrivateKeyProtected` is the operator's explicit attestation that this step was completed and checked.

## 4. Sign and verify replay acceptance

```powershell
.\scripts\run_rps_wp4_operator_replay_acceptance.ps1 `
    -Command accept-replay `
    -OperatorId $operatorId `
    -ConfirmPrivateKeyProtected
```

Expected status:

`COMPLETE_LOCAL_SIGNING_AND_REPLAY_ACCEPTANCE_CANDIDATE`

The command:

1. re-verifies every governed source and compute identity;
2. re-reads and hashes all 21 derived payloads;
3. creates the operator signing-binding candidate;
4. signs the canonical replay acceptance with Ed25519 SSHSIG namespace `ovc-rps`;
5. verifies the signature locally;
6. creates an RPS-G4 operator-gate input;
7. leaves ACTIVE_RESEARCH_TRIAGE false, write authority false and LIVE_PROSPECTIVE append denied.

## Output directory

The command reports an `acceptance_id`. The compact output is stored under:

```text
%OVC_EXTERNAL_ARTIFACT_ROOT%\prospective-source\replay-acceptance\<acceptance_id>\
```

## Return exactly four compact files

Upload only:

```text
operator-signing-binding.json
time-gated-replay-acceptance.json
signature-verification-receipt.json
rps-g4-operator-gate-input.json
```

Do not upload:

- `id_ed25519`;
- `id_ed25519.pub` unless separately requested by an approved operator-key registration procedure;
- any bar, C1, C2 state or transition payload;
- source CSV or BI5 bytes;
- machine-path listings;
- staging or quarantine directories.

After uploading the four compact files, issue:

`@GitHub OVC CONTINUE`

The next decision is RPS-G4. It is operator-required because it proposes ACTIVE_RESEARCH_TRIAGE and first LIVE_PROSPECTIVE operation authority.

## Failure behaviour

Any failure creates no accepted replay candidate. A new staging directory may be moved to the RPS-WP4 quarantine. Preserve it and report only the compact failure receipt or terminal error. Do not weaken byte checks, replace the key, delete a prior candidate or rerun with a different operator identity without a lawful resolution.

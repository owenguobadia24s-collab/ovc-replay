# C2AR-WP10 June vNext Full Replay — Operator Runbook

Status: `IMPLEMENTED_PENDING_OPERATOR_LOCAL_EXECUTION`  
Authority: inactive, noncanonical, operator-local research evidence only.  
Governing plan: `OVC-C2-ANATOMY-REDESIGN-IMPLEMENTATION / 0.3-REVISED`  
Continuation point: `C2AR-WP10_INPUT_RESOLUTION_BEFORE_REAL_OPPORTUNITY_BUILD`

## Purpose

This packet resolves the missing orchestration and binding-contract portion of `CEAR-G10-BLOCKER-001`. It does not resolve the blocker until the accepted June source bytes are present locally and the replay completes with identical clean-run and restart hashes.

The runner consumes only the accepted source slice:

- `RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1`
- context: `2026-05-30T00:00:00Z` to `2026-07-03T00:00:00Z`
- target: `2026-06-01T00:00:00Z` to `2026-07-01T00:00:00Z`
- clocks: `15M`, `2H_A_L`
- sides: `BID`, `ASK`

Legacy C2 states, transitions, CandidateWindow outputs and rule matches are prohibited inputs. The accepted M1 source and derived C1 records are rebuilt and hash-verified locally.

## Clean worktree

Use a clean worktree at the exact corrective branch head. Do not run from a detached dirty checkout and do not reset or delete unrelated local work.

```powershell
cd C:\Users\Owner\OVIS\ovc-replay
git fetch origin

$Worktree = "C:\Users\Owner\OVIS\ovc-replay-c2ar-wp10-replay"
if (-not (Test-Path $Worktree)) {
    git worktree add $Worktree origin/build/c2ar-wp10-input-resolution-full-replay
}
cd $Worktree
git status --short
```

The last command must produce no output.

## Environment

```powershell
$env:OVC_EXTERNAL_ARTIFACT_ROOT = "C:\Users\Owner\OVIS\ovc-replay-external-artifacts"
```

The accepted source slice must exist under:

```text
$env:OVC_EXTERNAL_ARTIFACT_ROOT\prospective-source\intake\RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1
```

## 1. Build the immutable input binding

```powershell
.\scripts\c2ar\run_vnext_full_replay.ps1 -Command build-binding
```

The builder verifies every source object and repository contract, schema, registry and implementation file before writing:

```text
$env:OVC_EXTERNAL_ARTIFACT_ROOT\c2-anatomy-redesign-v0-2\source-bindings\C2_VNEXT_FULL_REPLAY_INPUT_BINDING_v1.json
```

Do not edit the binding manually. Rebuild it when the intended code commit changes.

## 2. Preflight

```powershell
.\scripts\c2ar\run_vnext_full_replay.ps1 -Command preflight
```

Preflight fails closed for a code-head mismatch, missing or changed source bytes, changed repository bytes, authority drift, incomplete clock/side scope, or a binding-hash mismatch.

## 3. Execute

Use a new output path for every attempt. The default is:

```text
$env:OVC_EXTERNAL_ARTIFACT_ROOT\c2-anatomy-redesign-v0-2\wp10-rules\june-vnext-full-replay
```

```powershell
.\scripts\c2ar\run_vnext_full_replay.ps1 -Command execute
```

The command performs:

1. exact source and repository-byte verification;
2. deterministic M1 to 15M and `2H_A_L` reconstruction;
3. lawful C1 reconstruction with explicit continuity resets;
4. complete June opportunity accounting for every registered sequence length;
5. neutral fingerprints, motifs, provisional families and functional cores;
6. inactive declarative rule compilation, complete evaluation and exact-stratum controls;
7. two clean executions;
8. a bounded checkpoint interruption followed by restart;
9. logical-hash, count and artifact-inventory reconciliation;
10. runtime and output-capacity checks.

## Required terminal receipts

A successful output root contains:

```text
input-binding.json
preflight-receipt.json
run-001/output-manifest.json
run-001/capacity-receipt.json
run-002/output-manifest.json
run-002/capacity-receipt.json
restart-verification/output-manifest.json
restart-verification/capacity-receipt.json
determinism-receipt.json
restart-receipt.json
orchestration-receipt.json
```

`orchestration-receipt.json` must report `result: PASS`. The determinism and restart receipts must also report `PASS` with no discrepancies.

## Repository return packet

Do not commit bulk market, C1, opportunity, fingerprint, family, candidate or evaluation payloads. Commit only compact manifests, hashes, count reconciliations, capacity/restart receipts, QA evidence and the updated CEAR-G10 decision packet.

After the local run succeeds, return to the project with:

```text
OVC CONTINUE
```

## Authority boundary

A successful replay resolves input reproducibility only. It does not admit the discovery method, pass a functional or rule candidate, activate a selector, create an event or episode, publish a release, consume Validation, or grant probability, risk, exposure, trading, execution or agent-write authority. CEAR-G10 remains operator-required.

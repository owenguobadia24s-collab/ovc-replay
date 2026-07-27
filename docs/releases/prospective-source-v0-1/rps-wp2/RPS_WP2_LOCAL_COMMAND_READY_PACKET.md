# RPS-WP2 — Operator-Local Intake Command Ready

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-WP2`
- Baseline main: `b21228a8e43a3f5b4a49441991d0097b2e1908b6`
- Branch: `build/rps-wp2-local-intake-command`
- RPS-G1: `APPROVED`
- State: `READY_FOR_OPERATOR_LOCAL_EXECUTION`
- Real source slice available: `false`
- Tested implementation commit: `8885f474eba986ac5b95790ff95eebc6840cd65e`
- Canonical workflow: `30278066944` — `PASS`
- Delegated decision: `PASS`

## Delivered

- One operator-local Python command compiled to the exact RPS-G1 slice, interval, streams and limits.
- A Windows PowerShell wrapper with preflight and execute modes.
- Direct Dukascopy BI5 transport, decompression and deterministic logical-object construction derived from the existing `OVC_DIRECT_BI5_CANDLE_ADAPTER` policy.
- Exact compressed and expanded byte-limit enforcement.
- Four logical source-object IDs with deterministic CSV bytes, SHA-256, byte size, row count, schema fingerprint and boundary coverage.
- Strict ordering, duplicate, unexpected-gap, BID/ASK and native-H1 reconciliation checks.
- Staged non-overwriting freeze and quarantine-on-failure behaviour.
- Compact request, inventory, QA, reconciliation, manifest and freeze receipts.
- Explicit CI/GitHub Actions provider-execution denial.
- Focused fake-BI5 tests; no provider access is used by tests.
- Windows operator documentation.

## Exact command surface

```powershell
.\scripts\run_rps_wp2_intake.ps1 -Command preflight
.\scripts\run_rps_wp2_intake.ps1 -Command execute
```

Equivalent Python commands:

```powershell
.\.venv\Scripts\python.exe -m `
  ovc.research_operations.prospective_source.dukascopy_intake `
  preflight `
  --repository-root .

.\.venv\Scripts\python.exe -m `
  ovc.research_operations.prospective_source.dukascopy_intake `
  execute `
  --repository-root . `
  --gate RPS-G1
```

## Scope immutability

The command does not expose CLI options for changing:

- `RPS.DUKASCOPY.GBPUSD.20260724_20260727.v1`;
- `[2026-07-24T00:00:00Z, 2026-07-27T00:00:00Z)`;
- M1 BID, M1 ASK, native H1 BID and native H1 ASK;
- 25 MiB compressed or 100 MiB expanded limits.

A different source request requires a different approved gate and implementation identity.

## Tests and QA

Canonical workflow `30278066944` passed on tested implementation commit `8885f474eba986ac5b95790ff95eebc6840cd65e`. The workflow ran the full repository unittest discovery suite, including the bounded-intake fake-provider tests. No provider request occurred.

The command-readiness boundary is `PASS` under delegated AUTO-EXECUTABLE authority. Decision record: `RPS_WP2_COMMAND_READY_DELEGATED_DECISION.md`.

RPS-WP2 itself remains `RUNNING`; it is not complete until the operator creates and supplies the compact accepted source-slice evidence.

## Authority retained as denied

No provider request has been made by this implementation packet. No accepted real source slice exists yet.

The packet grants no ACTIVE_RESEARCH_TRIAGE, LIVE_PROSPECTIVE append, selector/release/R2 mutation, Validation consumption, active novelty ranking, semantic promotion, C2E/C2.5/C3, OPT-C/OPT-D, probability, risk, exposure, trading, execution or agent-write authority.

## Rollback

Revert the command-readiness squash merge. No provider object, source slice, release, selector, R2 key, evidence row or active authority is affected.

## Continuation point

The operator runs the documented local preflight and execute commands. After a successful freeze, provide only the compact manifest and receipts and issue `OVC CONTINUE`. Do not proceed to RPS-G2 without reproducible accepted-slice evidence.

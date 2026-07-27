# RPS-WP3 Windows Operator Guide

## Boundary

This command performs local derived computation only. It contacts no provider and creates no release, selector, R2 object, Validation input, LIVE_PROSPECTIVE row or ACTIVE_RESEARCH_TRIAGE authority.

It consumes only the accepted frozen source slice:

`RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`

The slice must remain under `OVC_EXTERNAL_ARTIFACT_ROOT` with the exact manifest, receipts and four source-object CSVs produced by RPS-G1B.

## Update the checkout

```powershell
cd C:\Users\Owner\OVIS\ovc-replay

git switch main
git pull --ff-only
git status --short
```

The tracked worktree must be clean.

## Set the external artifact root

```powershell
$env:OVC_EXTERNAL_ARTIFACT_ROOT = `
    "C:\Users\Owner\OVIS\ovc-replay-external-artifacts"
```

## Preflight

```powershell
.\scripts\run_rps_wp3_compute.ps1 -Command preflight
```

Expected status:

```text
READY_FOR_LOCAL_DERIVED_COMPUTE
```

Preflight verifies:

- the exact repository compact-evidence index;
- all nine compact files in the accepted source slice;
- the source manifest logical and file hashes;
- all four source-object identities, byte sizes and SHA-256 values;
- the clean `main` code commit;
- the GAPPED, NOT_A_RELEASE and denied-authority states.

It performs no output write and no network access.

## Execute

```powershell
.\scripts\run_rps_wp3_compute.ps1 -Command execute
```

Expected successful status:

```text
COMPLETE_LOCAL_PROSPECTIVE_COMPUTE_CANDIDATE
```

The command is compiled to RPS-G2 authority, the exact June slice, the exact cutoff, 15M and 2H_A_L, BID and ASK, and `TIME_GATED_REPLAY`. It cannot accept alternative source identities or dates through CLI options.

## Computation

The command:

1. re-verifies every frozen source and compact-evidence byte;
2. reads M1 BID and ASK;
3. builds all UTC-aligned 15M and 2H parents;
4. excludes the 17 incomplete 15M and 6 incomplete 2H parents per side;
5. runs `C1.FORMULAS.v0.1` on complete parents only;
6. runs the actual C2 Discovery structure/state engine for 2H local, 15M local and 15M-with-2H-parent scopes;
7. resets continuity at source gaps;
8. writes a deterministic payload manifest, compute-run record, source-binding candidate and receipt.

No repair, forward fill, interpolation or synthesis is performed.

## Output

A successful run is stored outside Git under:

```text
%OVC_EXTERNAL_ARTIFACT_ROOT%\prospective-source\compute\RPS.RUN.<24-hex>\
```

Key compact files:

```text
output-manifest.json
prospective-compute-run.json
prospective-source-binding.json
compute-receipt.json
qa\coverage.json
```

Derived record payloads remain outside Git under `bars/`, `c1/` and `c2/`.

## Required result states

The compact records must retain:

```text
operation_mode: TIME_GATED_REPLAY
release_status: NOT_A_RELEASE
selector_eligibility: NONE
r2_publication: DENIED
validation_consumption: DENIED
live_prospective_append: DENIED
active_research_triage: false
write_authority: false
```

The source binding is only `ACCEPTED_FOR_REPLAY_CANDIDATE`; it is not active.

## Failure handling

A failure moves only the new compute staging workspace to:

```text
%OVC_EXTERNAL_ARTIFACT_ROOT%\prospective-source\compute\quarantine\
```

The accepted source slice and both original intake quarantines remain untouched. Do not edit a failed compute quarantine or bypass its checks.

## Continuation evidence

After success, provide only:

- `output-manifest.json`;
- `prospective-compute-run.json`;
- `prospective-source-binding.json`;
- `compute-receipt.json`;
- `qa/coverage.json`.

Do not upload bars, C1/C2 JSONL payloads, source CSVs, BI5 objects or machine paths.

Then issue:

```text
@GitHub OVC CONTINUE
```

RPS-G3 remains unavailable until the compact compute evidence is reproduced and accepted.

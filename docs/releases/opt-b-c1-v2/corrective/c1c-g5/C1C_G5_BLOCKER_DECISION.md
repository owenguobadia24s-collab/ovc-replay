# C1C-G5 — partial PASS and corrective Pilot Discovery blocker

**Decision:** `BLOCK`

The operator-approved C1C-G5 execution reached its first non-correctable environment boundary after completing all repository and remote release-chain work.

## Completed

- Exact C1 v2 Discovery and Development parents were already remotely verified under workflow `30384400312`.
- The accepted C2 v1 semantic source artifact `8634383302` was full-byte verified.
- `404,434` C2 states and `323,910` transitions were rebound to the exact C1 v2 identities.
- Every C2 state and transition identity changed; semantic state drift and transition drift were both `0`.
- Two independent C2 v2 materializations were byte-identical.
- C2 v2 Discovery and Development releases were published payload-first and manifest-last.
- Workflow `30386243014` read back and SHA-256 verified `38` remote objects and `872,879,711` bytes.
- The coordinated C1/C2 v2 selector transaction is materialized and becomes atomic when PR #132 is squash-merged to `main`.
- The original noncanonical Pilot Discovery namespace is append-only superseded for lineage identity purposes; its evidence is preserved and remains non-promotable.

## Blocker

`C1C-G5-BLOCK-001` prevents the approved corrective Pilot Discovery rerun from being fabricated in GitHub Actions. The frozen operation requires:

- the exact operator-local compute root for `RPS.RUN.7aeb551335d766ee3bf503e6`;
- the private Ed25519 key bound by `RPS.SIGNING.50092c28981fef08f53a6cb5`; and
- a human review of the newly generated queue before signed finalization.

Those objects are intentionally unavailable to CI. The corrective runner and Windows wrapper are now implemented, but execution must occur on clean local `main` after the selector transaction merges.

## Exact local continuation

```powershell
.\scripts\run_c1c_g5_pilot_corrective_rerun.ps1 preflight
.\scripts\run_c1c_g5_pilot_corrective_rerun.ps1 execute -Gate C1C-G5
```

Complete the generated review file, then run:

```powershell
.\scripts\run_c1c_g5_pilot_corrective_rerun.ps1 finalize `
  -Gate C1C-G5 `
  -PilotRunId '<NEW_RUN_ID>' `
  -ReviewFile '<COMPLETED_REVIEW_FILE>'
```

Return the compact signed evidence files named in `C1C_G5_PILOT_SUPERSESSION_RERUN_BLOCKER.json`.

## Retained authority

Canonical Pattern Discovery append remains denied. Validation remains `LOCKED_UNCONSUMED`. No semantic, family, novelty or threshold promotion and no probability, risk, exposure, trading, execution or agent-write authority is granted.

## Rollback

The selector transaction can atomically restore the exact C1 v1 and C2 v1 selector identities while preserving all v2 releases immutable and inactive. Legacy B-state is never reactivated.

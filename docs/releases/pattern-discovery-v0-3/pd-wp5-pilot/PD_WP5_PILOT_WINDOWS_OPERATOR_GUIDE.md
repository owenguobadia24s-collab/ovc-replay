# PD-WP5-PILOT Windows Operator Guide

## Authority

This command is authorised only by `PD-G4B PASS` and only for one bounded:

```yaml
research_role: PILOT_DISCOVERY
operation_mode: TIME_GATED_REPLAY
source: RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1
pilot_only: true
promotion_eligibility: NON_PROMOTABLE
```

It cannot request provider data, write canonical Discovery evidence, relabel output `LIVE_PROSPECTIVE`, mutate C2, selectors or releases, publish R2, consume Validation, activate novelty ranking, promote semantics or families, or create probability, risk, exposure, trading, execution or agent authority.

## Required local state

1. Pull the merged PD-WP5-PILOT implementation onto a clean local `main`.
2. Confirm the existing external root is available:

   ```powershell
   $env:OVC_EXTERNAL_ARTIFACT_ROOT = 'C:\Users\Owner\OVIS\ovc-replay-external-artifacts'
   ```

3. Do not move, rename or edit the accepted June source, compute run, replay acceptance or operator key.
4. The runner verifies every accepted compute payload byte through the existing RPS-WP4 verifier before reading C2.

## 1. Preflight

```powershell
.\scripts\run_pd_wp5_pilot_discovery.ps1 preflight
```

Expected status:

```text
READY_FOR_PD_WP5_PILOT_EXECUTION
```

Preflight must resolve all of the following exact identities:

- `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`
- `RPS.RUN.7aeb551335d766ee3bf503e6`
- `RPS.BINDING.32fb3003efa072916c11e907`
- `RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48`
- `RPS.SIGNING.50092c28981fef08f53a6cb5`
- `OVC.OPERATOR.PRIMARY.LOCAL.V1`

Stop if preflight returns exit code `2`.

## 2. Execute the machine rehearsal

```powershell
.\scripts\run_pd_wp5_pilot_discovery.ps1 execute -Gate PD-G4B
```

The runner:

1. re-verifies the complete accepted compute manifest and all 21 payload files;
2. loads the exact June C2 state payloads without provider access;
3. evaluates triggers and transitions in first-valid chronology;
4. applies deterministic candidate-window and queue-cap controls;
5. constructs pilot-only fingerprints and provisional clusters;
6. builds the read-only Console bundle with the persistent pilot banner;
7. reruns the complete machine rehearsal and compares logical hashes;
8. signs the pilot run with the already bound operator Ed25519 key;
9. writes append-only output under:

   ```text
   OVC_EXTERNAL_ARTIFACT_ROOT\pattern-discovery\pilot\PD.PILOT.GBPUSD.20260622_20260625.v1\<pilot-run-id>
   ```

10. returns `PILOT_MACHINE_REHEARSAL_COMPLETE_AWAITING_OPERATOR_REVIEW`.

No existing run is overwritten. A failed staging directory is moved to `quarantine` with a failure receipt.

## 3. Review the Console projection

Open the generated `review\console-bundle.json` through the local Pattern Discovery Console surface. Every view must continuously display:

```text
PILOT_ONLY · NON_PROMOTABLE · TIME_GATED_REPLAY · GAPPED_SOURCE
```

Review every promoted queue item. Copy:

```text
review\pilot-review-input.template.json
```

to a separate completed review file and replace:

- `reviewed_at_utc` with the actual UTC review time;
- each `REPLACE_WITH_ALLOWED_DISPOSITION` with one of:
  - `WORKFLOW_ACCEPTED`
  - `FLAG_WORKFLOW_DEFECT`
  - `FLAG_UI_FRICTION`
  - `DEFER_PILOT_OBJECT`
  - `REJECT_PILOT_OBJECT`
- `notes` and `ui_friction_codes` with factual pilot findings.

Do not add outcome, return, probability, trade, exposure or execution judgments.

## 4. Finalise signed pilot evidence

```powershell
.\scripts\run_pd_wp5_pilot_discovery.ps1 finalize `
  -Gate PD-G4B `
  -PilotRunId '<pilot-run-id>' `
  -ReviewFile '<absolute-path-to-completed-review.json>'
```

The command requires a decision for every promoted candidate, signs the operator review and evidence inventory, and produces:

- `pilot-review-receipt.json`
- `pilot-defect-ledger.json`
- `signed-pilot-evidence-inventory.json`
- `pd-g5p-gate-input.json`

Return these four compact files together with `pilot-run.json`, `output-manifest.json` and `qa/pilot-qa.json` for PD-G5P evaluation. Do not commit raw C2, candidate, fingerprint, cluster or Console payloads.

## Stop boundary

After finalisation, stop at:

```text
PD-G5P — Pilot Discovery Operations Acceptance
```

Canonical 2021–2023 Discovery remains unavailable until an explicit PD-G5P PASS freezes the final contracts and authorises a complete reset of candidate, cluster, medoid, assignment, family and evidence identities.

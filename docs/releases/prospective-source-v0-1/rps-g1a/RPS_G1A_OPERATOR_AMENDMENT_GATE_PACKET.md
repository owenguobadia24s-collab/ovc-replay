# RPS-G1A — Real Provider Intake Scope Amendment

## Gate identity

- Gate: `RPS-G1A`
- Title: June completed-month replacement for unavailable July intake
- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- Plan version: `0.1`
- Packet: `RPS-WP2`
- Baseline main: `c61825aa6edc3389566e94316138391db49ac9d5`
- Candidate implementation commit: `2aaed61438da65000a45542e7bbd097d9433cc00`
- Approved tested branch head: `bf65fedcd1cf354641fa25f87f4ab5acb642cae7`
- Candidate branch: `build/rps-g1a-june-source-amendment`
- Pull request: `#101`
- Gate status: `APPROVED`
- Decision: `PASS`
- Authority: `OPERATOR`
- Approval command: `OVC APPROVE RPS-G1A`
- Decision record: `RPS_G1A_OPERATOR_DECISION.md`

## Completed work

1. Preserved the original July attempt as a provider-availability incident without committing machine paths, raw provider bytes or quarantine payloads.
2. Added an isolated RPS-G1A intake profile that reuses the accepted bounded BI5 implementation without mutating the historical RPS-G1 profile.
3. Bound the operator wrapper to the approved June slice and `RPS-G1A` gate.
4. Added exact fake-provider tests for the replacement interval and regression protection for the historical July profile.
5. Added a no-provider-access CI workflow definition.
6. Updated the machine-readable programme registry, replacement profile manifest and Windows operator guide.
7. Recorded the operator PASS decision and supersession of the unavailable July scope.

## Previous authority

The operator approved one exact July 2026 intake under `RPS-G1`. That request could not complete because the required current-month native-H1 provider object returned HTTP 404. No accepted source slice was created.

RPS-G1 is now superseded for intake execution. Its quarantined identity and bytes remain preserved and cannot be retried, relabelled or accepted under RPS-G1A.

## Approved authority delta

One exact operator-local Dukascopy request is authorised:

| Field | Approved RPS-G1A value |
|---|---|
| Provider | Dukascopy |
| Instrument | GBP/USD |
| Slice | `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1` |
| Source window | `[2026-06-22T00:00:00Z, 2026-06-25T00:00:00Z)` |
| Detailed objects | M1 BID and M1 ASK |
| Reconciliation controls | native H1 BID and native H1 ASK |
| Destination | `%OVC_EXTERNAL_ARTIFACT_ROOT%/prospective-source/intake/RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1/` |
| Request bound | Exactly four logical streams; no rolling backfill |
| Compressed limit | 25 MiB (`26214400` bytes) |
| Expanded limit | 100 MiB (`104857600` bytes) |
| Network location | Operator-local only; prohibited in CI |
| Result authority | Local immutable source slice only; `NOT_A_RELEASE` |

Approval withdraws authority to retry or accept the July identity under RPS-G1. The July quarantine remains evidence and cannot be relabelled, copied or reused as June data.

## Acceptance conditions

1. Provider, instrument, side, interval and adapter profile resolve exactly.
2. The replacement command exposes no CLI option for changing the approved scope.
3. M1 BID, M1 ASK, native H1 BID and native H1 ASK are all present.
4. Every source object records exact byte size, row count, SHA-256 and schema fingerprint.
5. Ordering, duplicate, boundary, gap, BID/ASK and native-H1 reconciliation checks pass.
6. No gap, H1 object or timestamp is filled, repaired or substituted.
7. The command aborts and quarantines on integrity failure or byte-limit breach.
8. The final slice remains local-only, `NOT_A_RELEASE`, selector-ineligible, R2-denied, Validation-denied and LIVE_PROSPECTIVE-denied.
9. Raw provider bytes, local quarantine payloads and machine paths remain outside Git.
10. Provider execution remains impossible in CI.

## Tests and QA

### Implemented checks

- exact replacement profile and interval assertions;
- three-day continuous M1 BID/ASK fake provider population;
- native H1 BID/ASK reconciliation from complete M1 hours;
- deterministic four-object manifest and source identity checks;
- wrong-gate rejection;
- CI provider-execution rejection;
- original July-profile non-mutation regression;
- canonical repository unittest discovery;
- no-network preflight.

### CI evidence

- Canonical workflow: `30281531558`
- Canonical job: `90028842735`
- Command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- Result: `PASS`
- Provider request performed: `false`

The canonical discovery suite included the June amendment tests. No provider request occurred.

### QA recommendation

`PASS`, accepted by the operator. The candidate is deterministic, bounded, non-activating and preserves every prohibited authority.

## Warnings and unresolved issues

- The June provider objects have not yet been requested locally.
- Actual byte sizes and provider content remain unknown until operator execution.
- A provider correction, gap, mismatch or unavailable object must quarantine the run; it cannot be silently repaired.
- The July local quarantine remains outside Git and must remain preserved by the operator.
- RPS-WP2 is not complete until the compact accepted June manifest and receipts are supplied.

## Changed files

- `src/ovc/research_operations/prospective_source/dukascopy_intake_rps_g1a.py`
- `tests/research_operations/prospective_source/test_dukascopy_intake_rps_g1a.py`
- `scripts/run_rps_wp2_intake.ps1`
- `.github/workflows/rps-g1a-june-source-amendment.yml`
- `docs/releases/prospective-source-v0-1/rps-g1a/RPS_G1A_PROVIDER_AVAILABILITY_INCIDENT.md`
- `docs/releases/prospective-source-v0-1/rps-g1a/RPS_G1A_REPLACEMENT_INTAKE_PROFILE.json`
- `docs/releases/prospective-source-v0-1/rps-g1a/RPS_G1A_OPERATOR_DECISION.md`
- `docs/releases/prospective-source-v0-1/rps-wp2/RPS_WP2_WINDOWS_OPERATOR_GUIDE.md`
- `registries/research_operations/prospective_source/REAL_PROSPECTIVE_SOURCE_IMPLEMENTATION_REGISTRY_v0_1.yaml`
- this gate packet

## External artifact hashes

None are admitted at this gate. The July quarantine remains operator-local and the June provider request has not occurred.

## Authority retained as denied

ACTIVE_RESEARCH_TRIAGE, LIVE_PROSPECTIVE append, live Pattern Discovery processing, active novelty ranking, selector/release/R2 mutation, Validation consumption, semantic or theory promotion, C2E/C2.5/C3, OPT-C/OPT-D, probability, risk, exposure, trading, execution and agent write remain denied.

## Rollback

Before a frozen June slice exists, withdraw RPS-G1A authority and revert the amendment merge. Preserve the July quarantine and any June failure incident. After a checksum-addressed June slice freezes, preserve it and its receipts while withdrawing downstream consumption authority.

## Decision

**PASS** — the exact June replacement scope is approved and the unavailable July intake authority is superseded.

## Exact work after approval

1. Squash-merge the bounded amendment PR into `main` after pinning the final head and verifying checks.
2. Pull the approved main tip locally.
3. Run the documented preflight and execute commands.
4. Supply only the compact June manifest and six compact receipt files.
5. Resume RPS-WP2 and evaluate RPS-G2.

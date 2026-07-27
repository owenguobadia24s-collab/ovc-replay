# RPS-G1A — Real Provider Intake Scope Amendment

## Gate identity

- Gate: `RPS-G1A`
- Title: June completed-month replacement for unavailable July intake
- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- Plan version: `0.1`
- Packet: `RPS-WP2`
- Baseline main: `c61825aa6edc3389566e94316138391db49ac9d5`
- Candidate implementation commit: `2aaed61438da65000a45542e7bbd097d9433cc00`
- Candidate gate branch head tested through PR merge ref: `4a4ae30692af6b226ef79add115646eb3ad5b8ce`
- Candidate branch: `build/rps-g1a-june-source-amendment`
- Pull request: `#101`
- Gate status: `GATE_READY`
- Authority: `OPERATOR_REQUIRED`

## Completed work

1. Preserved the original July attempt as a provider-availability incident without committing machine paths, raw provider bytes or quarantine payloads.
2. Added an isolated RPS-G1A intake profile that reuses the accepted bounded BI5 implementation without mutating the historical RPS-G1 profile.
3. Bound the operator wrapper to the proposed June slice and `RPS-G1A` gate.
4. Added exact fake-provider tests for the replacement interval and regression protection for the historical July profile.
5. Added a no-provider-access CI workflow definition.
6. Updated the machine-readable programme registry, replacement profile manifest and Windows operator guide.

## Current authority

The operator approved one exact July 2026 intake under `RPS-G1`. That request could not complete because the required current-month native-H1 provider object returned HTTP 404. No accepted source slice was created.

The July authority remains historical but unusable. It does not automatically transfer to another interval. Provider execution for the June candidate remains denied until this amendment gate passes.

## Proposed authority delta

Supersede only the unavailable RPS-G1 intake scope with one exact operator-local Dukascopy request:

| Field | Proposed RPS-G1A value |
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

Approval of RPS-G1A withdraws authority to retry or accept the July identity under RPS-G1. The July quarantine remains evidence and cannot be relabelled, copied or reused as June data.

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
10. Provider execution remains impossible in CI and before operator approval.

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

- Canonical workflow: `30281272345`
- Canonical job: `90027978323`
- Command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- Result: `PASS`

The canonical discovery suite included the new `test_dukascopy_intake_rps_g1a.py` file. Its tests exercise the exact June profile with generated fake BI5 objects, no-network preflight, wrong-gate rejection, CI execution denial and historical July-profile restoration. No provider request occurred.

The dedicated amendment workflow definition is included for future branch/default-branch execution; the canonical repository workflow supplied the gate's executed test evidence.

### QA recommendation

`PASS`. The candidate is deterministic, bounded, non-activating, tested without provider access and preserves every prohibited authority. No blocking warning or unresolved code defect remains inside the amendment packet.

## Warnings and unresolved issues

- The June provider objects have not been requested from this GitHub execution environment.
- Actual byte sizes and provider content are unknown until the operator executes locally after approval.
- A provider correction, gap, mismatch or unavailable object must quarantine the run; it cannot be silently repaired.
- The July local quarantine is outside Git and must remain preserved by the operator.

## Changed files

- `src/ovc/research_operations/prospective_source/dukascopy_intake_rps_g1a.py`
- `tests/research_operations/prospective_source/test_dukascopy_intake_rps_g1a.py`
- `scripts/run_rps_wp2_intake.ps1`
- `.github/workflows/rps-g1a-june-source-amendment.yml`
- `docs/releases/prospective-source-v0-1/rps-g1a/RPS_G1A_PROVIDER_AVAILABILITY_INCIDENT.md`
- `docs/releases/prospective-source-v0-1/rps-g1a/RPS_G1A_REPLACEMENT_INTAKE_PROFILE.json`
- `docs/releases/prospective-source-v0-1/rps-wp2/RPS_WP2_WINDOWS_OPERATOR_GUIDE.md`
- `registries/research_operations/prospective_source/REAL_PROSPECTIVE_SOURCE_IMPLEMENTATION_REGISTRY_v0_1.yaml`
- this gate packet

## External artifact hashes

None are admitted at this gate. The July quarantine remains operator-local and the June provider request has not occurred.

## Authority retained as denied

ACTIVE_RESEARCH_TRIAGE, LIVE_PROSPECTIVE append, live Pattern Discovery processing, active novelty ranking, selector/release/R2 mutation, Validation consumption, semantic or theory promotion, C2E/C2.5/C3, OPT-C/OPT-D, probability, risk, exposure, trading, execution and agent write remain denied.

## Rollback

Close PR #101 without merge and retain `main` at `c61825aa6edc3389566e94316138391db49ac9d5`. Preserve the July quarantine incident. No provider source, release, selector, R2 key, evidence row or active authority is changed by rollback.

## Recommended decision

**PASS** — approve the exact June replacement scope and supersede the unavailable July intake authority.

Allowed decisions: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`.

## Exact work after approval

1. Record the RPS-G1A operator decision and supersession of the July intake scope.
2. Pin the final PR head, confirm canonical checks remain PASS and squash-merge PR #101 into `main`.
3. Pull the approved main tip locally.
4. Run the documented preflight and execute commands.
5. Supply only the compact June manifest and six compact receipt files.
6. Resume RPS-WP2 and evaluate RPS-G2.

## Approval command

```text
OVC APPROVE RPS-G1A
```

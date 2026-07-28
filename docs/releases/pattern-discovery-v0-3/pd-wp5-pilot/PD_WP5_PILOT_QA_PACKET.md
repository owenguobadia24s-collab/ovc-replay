# PD-WP5-PILOT QA Packet

## Identity

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `PD-WP5-PILOT`
- Governing authority: `PD-G4B PASS`
- Baseline: `c46d9620e242c047dd8e203f91a1b00b542a2a81`
- Tested base: `8c243c009f30e453312861708afb784fe762c442`
- Tested candidate head: `3613709a4b073b0521a460b1d0c57d9ae2842cd5`
- PR: `#121`
- QA result: `PASS_IMPLEMENTATION_BLOCKED_LOCAL_EXECUTION`

## Scope reviewed

QA reviewed the operator-local implementation for one June 2026 `PILOT_DISCOVERY` `TIME_GATED_REPLAY` rehearsal using the exact accepted RPS-WP3 compute and RPS-WP4 signing chain.

## Tests

| Suite | Workflow | Job | Result |
|---|---:|---:|---|
| Focused Pilot Discovery implementation and full repository suite | `30353533468` | `90256328468` | PASS |
| Machine-readable schemas, authority boundary and fail-closed local-execution guards | `30353533468` | `90256328468` | PASS |

The decision-bearing job ran focused Pilot Discovery tests and the complete repository test suite against the PR merge containing current main `8c243c009f30e453312861708afb784fe762c442`. It also validated the packet schemas, prohibited provider access and canonical/promotion paths, and asserted clean-main, no-overwrite, deterministic-rerun and CI-denial controls.

## Functional acceptance

| Requirement | Result |
|---|---|
| Exact June source, compute, binding, replay acceptance and signing identities hard-bound | PASS |
| Full RPS-WP4 compute payload verification reused | PASS |
| Provider access absent | PASS |
| First-valid transition and trigger evaluation | PASS on governed fixture |
| Candidate-window lifecycle and queue caps | PASS on governed fixture |
| Pilot-only fingerprints and provisional clustering | PASS on governed fixture |
| Complete deterministic machine rerun comparison | PASS |
| Persistent Console pilot banner | PASS |
| Operator review template requires every promoted candidate | PASS |
| Existing Ed25519 binding used; private key remains external | PASS |
| Append-only output and quarantine handling | PASS |
| Compact PD-G5P input generation implemented | PASS |

## Authority and contamination controls

Every generated transition, trigger, candidate, fingerprint, cluster, queue item, review decision and evidence inventory is required to carry:

```yaml
research_role: PILOT_DISCOVERY
operation_mode: TIME_GATED_REPLAY
pilot_only: true
promotion_eligibility: NON_PROMOTABLE
canonical_discovery_population: false
live_prospective: false
identity_namespace: PD.PILOT.GBPUSD.20260622_20260625.v1
```

The implementation denies canonical append, LIVE_PROSPECTIVE relabelling, semantic/family promotion, active novelty ranking, selector/release/R2 mutation, Validation use, probability, risk, exposure, trading, execution and agent writes.

## External execution blocker

GitHub Actions cannot access:

- `C:\Users\Owner\OVIS\ovc-replay-external-artifacts`;
- the accepted 5,557,327-byte RPS-WP3 derived payload;
- the private Ed25519 key bound to `RPS.SIGNING.50092c28981fef08f53a6cb5`;
- the human operator required to review the generated Console queue.

Therefore QA does not claim that the real June pilot has executed. CI fixture success proves implementation readiness only.

## Smallest lawful resolution

After this packet is integrated:

```powershell
git switch main
git pull --ff-only
$env:OVC_EXTERNAL_ARTIFACT_ROOT = 'C:\Users\Owner\OVIS\ovc-replay-external-artifacts'
.\scripts\run_pd_wp5_pilot_discovery.ps1 preflight
.\scripts\run_pd_wp5_pilot_discovery.ps1 execute -Gate PD-G4B
```

Complete the generated `pilot-review-input.template.json`, then run `finalize` as specified in the operator guide. Return the seven compact files for PD-G5P. Do not return or commit raw pilot payloads.

## Warnings

1. The source is GAPPED; no fill, repair, interpolation or synthesis is permitted.
2. The three-day sample cannot establish family, semantic or market conclusions.
3. Fixture success cannot substitute for the exact accepted June compute bytes.
4. A machine-successful pilot remains incomplete until operator review and signed finalisation complete.
5. PD-G5P remains operator-required and canonical 2021–2023 Discovery remains unavailable.
6. Historical workflows that assert pre-Pilot registry state are not decision-bearing for this packet; the packet-specific workflow and full repository suite are the acceptance evidence.

## Rollback

Disable the pilot command, preserve and quarantine any generated pilot output, revert the implementation packet, prohibit every pilot identity from canonical import and retain the PD-G4B approval and historical RPS-G4A evidence.

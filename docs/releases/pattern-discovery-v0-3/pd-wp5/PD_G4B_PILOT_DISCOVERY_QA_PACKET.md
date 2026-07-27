# PD-G4B Pilot Discovery Amendment QA Packet

## QA identity

- Gate: `PD-G4B`
- Packet: `PD-WP5-PILOT`
- Baseline main: `0c177560b02e14a36a949626b155f616c12549e5`
- Branch: `gate/pd-g4b-pilot-discovery-amendment`
- QA status: `PASS_RECOMMEND_OPERATOR_AMENDMENT`
- Authority changed by this packet: none until operator approval

## Scope reviewed

QA reviewed the proposed replacement of the first `LIVE_PROSPECTIVE` PD-WP5 operation with one `PILOT_DISCOVERY` `TIME_GATED_REPLAY` operation using the existing signed June evidence chain.

## Exact lineage assertions

| Check | Required | Result |
|---|---|---|
| Source slice | `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1` | PASS |
| Coverage state | `GAPPED` | PASS |
| Compute run | `RPS.RUN.7aeb551335d766ee3bf503e6` | PASS |
| Source binding | `RPS.BINDING.32fb3003efa072916c11e907` | PASS |
| Signed replay acceptance | `RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48` | PASS |
| Signing binding | `RPS.SIGNING.50092c28981fef08f53a6cb5` | PASS |
| Operation mode | `TIME_GATED_REPLAY` | PASS |
| Research role | `PILOT_DISCOVERY` | PASS |
| Provider request required | no | PASS |
| New source or compute identity permitted | no | PASS |

## Authority assertions

- Pilot outputs are marked `PILOT_ONLY`: PASS.
- Pilot outputs are `NON_PROMOTABLE`: PASS.
- Canonical Discovery population membership is false: PASS.
- Canonical append remains denied: PASS.
- Signed capture is limited to a dedicated pilot namespace: PASS.
- Live relabelling remains denied: PASS.
- Identity reset before canonical Discovery is mandatory: PASS.
- RPS-G4A is superseded only for the pilot route: PASS.
- Genuine live intake is deferred to a separate future gate: PASS.

## Operational correction scope

The contract permits correction of workflow, UI, queue, batching, missingness, manifest, identity, deterministic and clustering-operation defects. It blocks outcome-selected threshold, distance, queue-cap or cluster-count tuning. PASS.

## Chronology and leakage

The contract requires first-valid cutoff enforcement and prohibits future information from trigger, window, fingerprint, distance, cluster, medoid, assignment and queue identity. Post-window information may appear only after those records are frozen and only in a separate pilot-review surface. PASS.

## Console and evidence separation

The required Console banner and pilot namespace prevent June pilot records from appearing as canonical Discovery evidence. The pilot cannot seed final families, semantic promotion, novelty ranking or 2021–2023 population counts. PASS.

## Gate sequence

The proposed sequence is:

`PD-G4B operator approval -> PD-WP5-PILOT -> PD-G5P operator acceptance -> final contract freeze and identity reset -> PD-WP5-CANONICAL`

This keeps the canonical 2021–2023 Discovery population unavailable until the pilot operating contract is reviewed and frozen. PASS.

## Retained prohibitions

Selector, release, R2, Validation, C2 mutation, C2E, C2.5, C3, OPT-C, OPT-D, semantic promotion, family promotion, active novelty ranking, probability, risk, exposure, trading, execution, autonomous processing and agent write remain denied. PASS.

## Warnings

1. The source is GAPPED. Pilot review must test missingness presentation and excluded-parent handling; it may not infer absent records.
2. The pilot is a short three-day sample and cannot establish population stability, family structure or market conclusions.
3. Operational changes discovered by the pilot may require versioned contract changes before canonical Discovery.
4. A successful pilot proves workflow readiness only; it does not prove the clustering or candidate definitions are substantively useful across 2021–2023.
5. The existing active authority record still names a first LIVE_PROSPECTIVE operation; it must be amended only after PD-G4B PASS.

## Unresolved issues

No blocking inconsistency remains in the amendment packet itself. Pilot implementation and execution are intentionally unavailable pending operator approval.

## Recommendation

`PASS` PD-G4B for one bounded Pilot Discovery operation, then stop at PD-G5P.

## Rollback

Revert the amendment files and state transitions, restore the prior live-source blocker as current, and preserve all historical source, compute, signing, blocker and quarantine evidence.

# PD-G4B — Pilot Discovery Contract Amendment Operator Gate

## Gate identity

- Gate ID: `PD-G4B`
- Gate title: `Pilot Discovery Contract Amendment`
- Governing plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- Pattern Discovery plan: `OVC_C2_PATTERN_DISCOVERY_AND_REVIEW_LAYER` v0.3
- Baseline main: `0c177560b02e14a36a949626b155f616c12549e5`
- Candidate branch: `gate/pd-g4b-pilot-discovery-amendment`
- Tested candidate head: `1c55524754d6cd457ea8e60a6478206bb89aa886`
- Pull request: `#117`
- Decision authority: `OPERATOR`
- Allowed decisions: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`

## Decision requested

Approve or reject a change to the frozen first-operation contract for PD-WP5.

A `PASS` defines the first operation as:

```yaml
research_role: PILOT_DISCOVERY
operation_mode: TIME_GATED_REPLAY
source: RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1
operation_limit: 1
pilot_only: true
promotion_eligibility: NON_PROMOTABLE
canonical_discovery_population: false
```

The pilot is one complete operational rehearsal before the canonical 2021–2023 Discovery population.

## Current authority

RPS-G4 remains active with:

- research line `RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1`;
- active model `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`;
- source binding `RPS.BINDING.32fb3003efa072916c11e907`;
- signing binding `RPS.SIGNING.50092c28981fef08f53a6cb5`;
- operator `OVC.OPERATOR.PRIMARY.LOCAL.V1`;
- ACTIVE_RESEARCH_TRIAGE true;
- canonical append false;
- live append false.

No pilot operation, provider request, canonical append or new authority has occurred.

## Exact pilot lineage

| Object | Exact identity |
|---|---|
| Source slice | `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1` |
| Source coverage | `GAPPED` |
| Source manifest | `429b7b568b7a43d04893c1873773f0b1b567730f2d5d4122d6a1c06dd40e3e41` |
| Compute run | `RPS.RUN.7aeb551335d766ee3bf503e6` |
| Output manifest | `3c6295badd04896a9e94b4b5a3ccb354bb51de52d5927839a86f61a40ed679ff` |
| Source binding | `RPS.BINDING.32fb3003efa072916c11e907` |
| Signed replay acceptance | `RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48` |
| Signing binding | `RPS.SIGNING.50092c28981fef08f53a6cb5` |
| Operator | `OVC.OPERATOR.PRIMARY.LOCAL.V1` |
| Admissible cutoff | `2026-06-25T00:00:00Z` |

No replacement source, compute run, signing identity or provider request is permitted.

## Purpose

The pilot must rehearse:

1. trigger evaluation;
2. candidate-window construction;
3. queue caps, suppression, merging, batching and backpressure;
4. fingerprint construction;
5. provisional clustering;
6. candidate, cluster, medoid and assignment identity generation;
7. operator review;
8. Research Console projection;
9. signed pilot-evidence capture;
10. deterministic rerun and evidence verification.

## Corrections permitted

A `PASS` permits versioned correction of:

- workflow defects;
- UI and review friction;
- queue-cap and batching problems;
- missingness and coverage handling;
- manifest, receipt and identity defects;
- deterministic reproducibility defects;
- clustering implementation defects;
- clustering runtime, memory and operational performance problems.

Observed June outcomes may not be used to select thresholds, distance weights, queue caps, cluster counts or definitions for favourable market results.

## Mandatory markings and identity isolation

Every June candidate, cluster, medoid, assignment, queue item, review decision, Console projection and evidence record must state:

- `research_role = PILOT_DISCOVERY`;
- `operation_mode = TIME_GATED_REPLAY`;
- `pilot_only = true`;
- `promotion_eligibility = NON_PROMOTABLE`;
- `canonical_discovery_population = false`;
- `live_prospective = false`.

Pilot identities must be isolated under `PD.PILOT.GBPUSD.20260622_20260625.v1`. Before canonical Discovery, all candidate, cluster, medoid, assignment, family and evidence identities must be reset under a new canonical namespace.

## Authority granted by PASS

A `PASS` authorises only:

1. implementation and execution of one operator-supervised Pilot Discovery operation;
2. read-only use of the exact existing source, compute and C2 payloads;
3. pilot-only trigger, candidate, queue, fingerprint and provisional-cluster computation;
4. pilot-only Console projection with a persistent pilot banner;
5. operator-signed append-only capture in a dedicated pilot namespace;
6. correction and deterministic rerun of defects inside the listed scope;
7. preparation of the `PD-G5P` packet;
8. mandatory stop at `PD-G5P`.

## Authority not granted

A `PASS` does not authorise:

- canonical 2021–2023 Discovery processing;
- June pilot outputs in canonical population or family counts;
- reuse of pilot candidate, cluster, medoid, assignment, family or evidence IDs;
- final trajectory-family definition;
- semantic, archetype, theory or family promotion;
- outcome-selected threshold or parameter tuning;
- active novelty ranking;
- C2 mutation, C2E, C2.5, C3, OPT-C or OPT-D;
- selector or release mutation;
- R2 publication;
- Validation consumption;
- probability, risk, exposure, trading or execution;
- autonomous processing or agent writes;
- provider access or a new source request;
- relabelling pilot output as `LIVE_PROSPECTIVE`.

## RPS-G4A disposition

RPS-G4A becomes `SUPERSEDED_FOR_PILOT_DISCOVERY` for the first PD-WP5 operation only. Its historical blocker and evidence remain preserved.

Genuine post-activation live-source intake and operation remain deferred to a separate operator gate, provisionally `RPS-LIVE-G1`. PD-G4B grants no live-source or provider authority.

## Acceptance conditions

PD-G4B may pass only if the operator accepts:

1. the exact June source, run, binding, signed acceptance, signing binding and operator;
2. `PILOT_DISCOVERY` and `TIME_GATED_REPLAY` as the first-operation role and mode;
3. one-operation scope;
4. `PILOT_ONLY` and `NON_PROMOTABLE` markings on every output;
5. dedicated pilot evidence and identity namespaces;
6. no canonical counts, family definitions or identity reuse;
7. first-valid chronology and future-data exclusion;
8. explicit GAPPED-source presentation and incomplete-parent exclusion;
9. versioned corrections only within the stated operational scope;
10. no outcome-selected tuning;
11. final contract freeze and complete identity reset before canonical Discovery;
12. mandatory stop at `PD-G5P`;
13. retained prohibition of every promotion, exposure and execution authority.

## Required PD-G5P evidence

The Pilot Discovery Operations Acceptance packet must contain:

- pilot run and output manifests;
- candidate, exclusion, queue, cluster, medoid and assignment inventories;
- deterministic rerun comparison;
- queue-cap, batching, runtime and memory evidence;
- missingness and coverage handling evidence;
- Console and operator-review findings;
- signed pilot-evidence inventory;
- defect/correction ledger;
- final contract candidate;
- exact canonical identity-reset procedure;
- unresolved warnings and rollback.

## Tests and QA

| Suite | Workflow | Job | Result |
|---|---:|---:|---|
| Pilot Discovery amendment, schema, payload guard and retained prohibitions | `30307255995` | `90114384840` | PASS |
| Historical first-live blocker preservation and Pilot supersession | `30307256074` | `90114385057` | PASS |
| Canonical repository suite | `30307255967` | `90114384730` | PASS |

QA recommendation: `PASS_RECOMMEND_OPERATOR_AMENDMENT`.

QA packet: `docs/releases/pattern-discovery-v0-3/pd-wp5/PD_G4B_PILOT_DISCOVERY_QA_PACKET.md`.

## Changed files

The branch contains only contracts, schemas, machine-readable state, gate/QA/implementation records, focused tests and CI assertions. It contains no market data, provider response, private key, source payload, C1/C2 stream, pilot candidate or evidence record.

## Warnings

1. The three-day GAPPED sample is too small to support market or family conclusions.
2. Pilot success proves workflow readiness only, not canonical population stability or usefulness.
3. The pilot may require a versioned final contract change at PD-G5P.
4. Signed pilot evidence is operational QA evidence, not canonical Discovery evidence.
5. The active authority record remains unchanged until PD-G4B PASS.

## Unresolved issues

No blocking inconsistency remains in the amendment packet. Pilot implementation and execution are intentionally absent pending operator approval.

## Rollback

Before execution, revert the amendment and restore the prior RPS-G4A/live blocker state. After execution, preserve and seal or quarantine all pilot outputs, prohibit canonical identity reuse, and require a new operator decision before canonical Discovery.

## Recommended decision

`PASS`.

## Exact work after approval

1. record the PD-G4B operator decision;
2. merge this amendment packet;
3. create a bounded PD-WP5-PILOT implementation branch from current main;
4. implement the operator-local pilot runner, Console projection and pilot evidence namespace;
5. run focused and canonical tests;
6. execute one pilot against the exact June chain;
7. repair correctable defects within scope and rerun;
8. materialise the pilot review and final contract-freeze candidate;
9. stop at `PD-G5P`.

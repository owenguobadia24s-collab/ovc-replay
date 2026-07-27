# PD-G4B — Pilot Discovery Contract Amendment Operator Gate

## Gate identity

- Gate ID: `PD-G4B`
- Gate title: `Pilot Discovery Contract Amendment`
- Governing plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- Pattern Discovery plan: `OVC_C2_PATTERN_DISCOVERY_AND_REVIEW_LAYER` v0.3
- Baseline main: `0c177560b02e14a36a949626b155f616c12549e5`
- Candidate branch: `gate/pd-g4b-pilot-discovery-amendment`
- Decision authority: `OPERATOR`
- Allowed decisions: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`

## Decision requested

Approve or reject a change to the frozen PD-WP5 first-operation contract.

A `PASS` redefines the first PD-WP5 operation as:

```yaml
research_role: PILOT_DISCOVERY
operation_mode: TIME_GATED_REPLAY
source: RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1
operation_limit: 1
pilot_only: true
promotion_eligibility: NON_PROMOTABLE
```

The pilot is one complete operational rehearsal before the canonical 2021–2023 Discovery population.

## Baseline and current authority

RPS-G4 is approved and active with:

- research line `RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1`;
- active model `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`;
- source binding `RPS.BINDING.32fb3003efa072916c11e907`;
- signing binding `RPS.SIGNING.50092c28981fef08f53a6cb5`;
- operator `OVC.OPERATOR.PRIMARY.LOCAL.V1`;
- ACTIVE_RESEARCH_TRIAGE true;
- canonical append false;
- live append false.

The previous PD-WP5 contract required the first operation to be genuinely post-activation `LIVE_PROSPECTIVE`. The active June binding could not satisfy that chronology, so the repository recorded a lawful blocker and prepared RPS-G4A.

No pilot operation, provider request, canonical append or authority change has occurred.

## Exact existing evidence chain

The pilot is bound to:

| Object | Identity |
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

No new source, compute or signature operation is needed to authorise the pilot implementation.

## Purpose of the pilot

Run one complete rehearsal of:

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

The pilot exists to make the operating workflow concrete and expose defects before the canonical 2021–2023 population is processed.

## Proposed correction authority

A `PASS` permits the pilot to identify and correct:

- workflow defects;
- UI and review friction;
- queue-cap and batching problems;
- missingness and coverage handling;
- manifest, receipt and identity defects;
- deterministic reproducibility defects;
- clustering implementation defects;
- clustering runtime, memory and operational performance problems.

Corrections must be versioned and rerun. Observed June outcomes may not be used to select thresholds, distance weights, queue caps, cluster counts or other definitions for favourable market results.

## Pilot markings and namespace

Every June candidate, cluster, medoid, assignment, queue item, review decision, Console projection and evidence record must state:

- `research_role = PILOT_DISCOVERY`;
- `operation_mode = TIME_GATED_REPLAY`;
- `pilot_only = true`;
- `promotion_eligibility = NON_PROMOTABLE`;
- `canonical_discovery_population = false`;
- `live_prospective = false`.

Pilot identities must be isolated under `PD.PILOT.GBPUSD.20260622_20260625.v1` or a deterministic child namespace. No pilot identity may be imported into the canonical 2021–2023 run.

## Authority granted by PASS

A `PASS` authorises only:

1. implementation and execution of one bounded operator-supervised Pilot Discovery operation;
2. read-only use of the exact existing source, compute and C2 payloads;
3. pilot-only trigger, candidate, queue, fingerprint and provisional cluster computation;
4. pilot-only Console projection;
5. operator-signed append-only evidence capture in a dedicated pilot namespace;
6. correction and deterministic rerun of defects inside the listed pilot scope;
7. creation of the `PD-G5P` decision packet;
8. mandatory stop at `PD-G5P`.

## Authority not granted

A `PASS` does not authorise:

- canonical 2021–2023 Discovery processing;
- inclusion of June pilot outputs in canonical population counts;
- reuse of pilot candidates, clusters, medoids, assignments, families or evidence IDs;
- final trajectory-family definition or promotion;
- semantic, archetype or theory promotion;
- outcome-selected threshold or parameter tuning;
- active novelty ranking;
- C2 mutation, C2E, C2.5, C3, OPT-C or OPT-D;
- selector or release mutation;
- R2 publication;
- Validation consumption;
- probability, risk, exposure, trading or execution;
- autonomous processing or agent writes;
- provider access or a new source request;
- relabelling any pilot output as `LIVE_PROSPECTIVE`.

## RPS-G4A disposition

RPS-G4A becomes `SUPERSEDED_FOR_PILOT_DISCOVERY` for the first PD-WP5 operation. Its historical blocker, proposal and evidence remain preserved.

A genuine post-activation live-source intake and operation remain deferred to a new separate operator gate, provisionally `RPS-LIVE-G1`. PD-G4B grants no live-source or provider authority.

## Acceptance conditions

PD-G4B may pass only if the operator accepts:

1. the exact June source, run, binding, signed acceptance, signing binding and operator identity;
2. `PILOT_DISCOVERY` and `TIME_GATED_REPLAY` as the first-operation role and mode;
3. one-operation scope;
4. `PILOT_ONLY` and `NON_PROMOTABLE` markings on every output;
5. dedicated pilot evidence and identity namespaces;
6. no canonical Discovery counts, family definitions or identity reuse;
7. chronology and future-data exclusion during candidate and clustering construction;
8. explicit GAPPED-source presentation and incomplete-parent exclusion;
9. versioned corrections only within the stated operational scope;
10. no outcome-selected tuning;
11. final contract freeze and complete identity reset before canonical Discovery;
12. mandatory stop at `PD-G5P`;
13. retained prohibition of every market-promotion, exposure and execution authority.

## Required PD-G5P evidence

The pilot acceptance packet must contain:

- pilot run and output manifests;
- candidate, exclusion, queue, cluster, medoid and assignment inventories;
- deterministic rerun comparison;
- queue-cap, batching and performance evidence;
- missingness and coverage handling evidence;
- Console and operator-review findings;
- signed pilot-evidence inventory;
- defect/correction ledger;
- final contract candidate;
- exact canonical identity-reset procedure;
- unresolved warnings and rollback.

## Changed files

The amendment branch contains only:

- the Pilot Discovery operation contract;
- machine-readable PD-G4B and PD-G5P states and schema;
- PD-WP5 and RPS-G4A state amendments;
- implementation, QA, supersession and gate packets;
- focused tests and CI assertions.

No market data, provider request, private key, source payload, C1/C2 stream, pilot candidate or evidence record is committed.

## Tests and QA

- Focused amendment tests: pending GitHub Actions on the final gate-ready head.
- Canonical repository suite: pending GitHub Actions on the final gate-ready head.
- QA recommendation: `PASS_RECOMMEND_OPERATOR_AMENDMENT`.
- QA packet: `docs/releases/pattern-discovery-v0-3/pd-wp5/PD_G4B_PILOT_DISCOVERY_QA_PACKET.md`.

The tested workflow and job IDs will be pinned before the gate is presented as final.

## Warnings

1. The three-day GAPPED sample is too small to support market or family conclusions.
2. Pilot operational success does not prove canonical population usefulness or stability.
3. The pilot may expose changes that require another versioned final-freeze decision at PD-G5P.
4. Signed pilot evidence remains operational evidence, not canonical Discovery evidence.
5. The current active authority record still names a live first operation and must be amended only after PD-G4B PASS.

## Unresolved issues

No blocking inconsistency is known in the amendment proposal. Pilot implementation is intentionally absent pending operator approval.

## Rollback

Before pilot execution, revert the amendment and restore the prior RPS-G4A/live-operation blocker state. After execution, preserve and seal or quarantine all pilot outputs, deny canonical identity reuse, and require a new operator decision before canonical Discovery.

## Recommended decision

`PASS`.

## Exact work after approval

1. record the PD-G4B operator decision;
2. merge the amendment packet;
3. create the bounded PD-WP5-PILOT implementation branch from current main;
4. implement the operator-local pilot runner, Console projection and pilot evidence namespace;
5. run focused and canonical tests;
6. execute one pilot against the exact June chain;
7. repair correctable defects inside scope and rerun;
8. materialise the final pilot review and contract freeze candidate;
9. stop at `PD-G5P`.

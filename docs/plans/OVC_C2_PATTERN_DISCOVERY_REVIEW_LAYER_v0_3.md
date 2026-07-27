# OVC C2 Pattern Discovery and Review Layer v0.3

Status: `PROPOSED_FOR_PD_G0`

Baseline: `main@9fb4c07984df2d5151c48b5b5d063789d9a594f1`

## Decision

Build a Research Operations layer that consumes canonical C2 records read-only and produces deterministic transition indexes, trigger events, candidate windows, trigger/completed fingerprints, novelty projections, provisional clusters and a small human review queue.

C2 remains canonical descriptive state. This layer is derived and replaceable. It may not create C2E episodes, C3 semantics, outcomes, probabilities, exposure, trading or execution authority.

## Programme

1. `PD-00` — authority, dependencies and implementation freeze.
2. `PD-00A` — scale, backpressure, controls, failure and degradation contract.
3. `PD-00B` — clustering algorithm and distance-pack decision.
4. `PD-WP1` — transition and candidate-window engine.
5. `PD-WP2` — trigger, control and novelty engine.
6. `PD-WP3` — fingerprints, deterministic clustering and non-evidentiary replay.
7. `PD-WP4` — simple Queue / Candidate Detail / Clusters UI and governed evidence bridge.
8. `PD-WP5` — first prospective discovery batch.

## Permanent boundaries

- Inputs: exact active C2 Discovery release, its C1/OPT-A lineage, approved Research Operations read models and QA assertions.
- Prohibited inputs: future returns, MFE/MAE, OPT-C/D outcomes, old 202 stories, old 58 candidates, B-STATE, C2E, C2.5, C3 and operator semantic labels.
- Candidate is not evidence.
- Cluster is not archetype.
- Trigger is not episode.
- Novelty does not rank until a separately approved activation gate.
- Controls are mandatory.
- Every object retains exact source, cutoff, configuration and algorithm lineage.

## Simple UI target

The first UI contains only:

- **Queue** — bounded candidate list, filters and dismiss/defer/control actions.
- **Candidate Detail** — source/authority strip, compact price strip, transition timeline, trigger explanation, fingerprint, nearest cluster and evidence form.
- **Clusters** — provisional cluster list, medoid, members, dispersion, controls and assignment challenges.

TradingView remains the primary external charting surface. The embedded strip is contextual only and must use exact OPT-A bars resolved through the candidate lineage.

## Gate rule

`PD-G0` may freeze design and permit bounded implementation only. It changes no market, selector, release, semantic, evidence-counting, probability, exposure, trading or execution authority.
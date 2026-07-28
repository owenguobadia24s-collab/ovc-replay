# PD-WP5 Pilot Discovery Operation Contract v0.1

## Governing amendment

- Amendment gate: `PD-G4B`
- Pilot acceptance gate: `PD-G5P`
- Governing plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- Pattern Discovery plan: `OVC_C2_PATTERN_DISCOVERY_AND_REVIEW_LAYER` v0.3
- Research role: `PILOT_DISCOVERY`
- Operation mode: `TIME_GATED_REPLAY`
- Operation limit: one complete pilot rehearsal

This contract replaces the requirement that the first PD-WP5 operation be `LIVE_PROSPECTIVE`. The earlier live-operation contract remains historical evidence but is superseded for the first PD-WP5 operation. Genuine post-activation live intake and operation remain deferred to a separate operator gate.

## Exact pilot binding

The pilot may use only the already accepted and signed June replay chain:

- source slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`;
- source coverage state: `GAPPED`;
- source manifest SHA-256: `429b7b568b7a43d04893c1873773f0b1b567730f2d5d4122d6a1c06dd40e3e41`;
- compute run: `RPS.RUN.7aeb551335d766ee3bf503e6`;
- output manifest SHA-256: `3c6295badd04896a9e94b4b5a3ccb354bb51de52d5927839a86f61a40ed679ff`;
- source binding: `RPS.BINDING.32fb3003efa072916c11e907`;
- signed replay acceptance: `RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48`;
- signing binding: `RPS.SIGNING.50092c28981fef08f53a6cb5`;
- operator: `OVC.OPERATOR.PRIMARY.LOCAL.V1`;
- active C2 model release: `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`;
- admissible cutoff: `2026-06-25T00:00:00Z`.

No new provider request, source slice, compute run, model release, signing binding or operator identity may be substituted under this contract.

## Purpose

Run one complete operational rehearsal before processing the canonical 2021–2023 Discovery population. The rehearsal must exercise:

1. trigger evaluation;
2. candidate-window construction;
3. queue caps, suppression, merging, batching and backpressure;
4. deterministic fingerprint construction;
5. provisional distance calculation and clustering;
6. candidate, cluster, medoid and assignment identity generation;
7. operator review workflow;
8. Research Console projection;
9. signed pilot-evidence capture;
10. manifest, receipt, lineage and deterministic rerun verification.

## Pilot correction authority

The pilot may identify and correct:

- workflow defects;
- UI and review friction;
- queue-cap and batching problems;
- missingness and coverage handling;
- manifest, receipt and identity defects;
- deterministic reproducibility defects;
- clustering implementation defects;
- clustering runtime, memory and operational performance problems.

Corrections must be versioned. A correction may not be justified by selecting the behaviour that looks most favourable against later June market outcomes. Any change to trigger definitions, window rules, queue caps, fingerprint formulas, distance semantics, clustering objective, cluster-count selection, batching limits or review disposition vocabulary must be included in the final pilot review and frozen before canonical Discovery begins.

## Chronology and leakage controls

At every replay timestamp `T`:

- trigger evaluation may read only records first-valid at or before `T`;
- candidate-window construction may read only the declared bounded window;
- future bars and later outcomes may not influence trigger identity, window identity, fingerprint, distance, cluster, medoid, assignment or review-queue ordering;
- post-window information may appear only in a separately labelled pilot-review surface after the candidate and clustering records are frozen;
- missing and incomplete parents remain unavailable; no fill, repair, interpolation or synthesis is permitted.

## Mandatory pilot markings

Every pilot candidate, cluster, medoid, assignment, queue item, review decision, Console projection and evidence record must carry:

```yaml
research_role: PILOT_DISCOVERY
operation_mode: TIME_GATED_REPLAY
pilot_only: true
promotion_eligibility: NON_PROMOTABLE
canonical_discovery_population: false
live_prospective: false
```

Pilot records must use a pilot namespace that cannot collide with canonical Discovery identities. The canonical 2021–2023 run must generate new candidate, cluster, medoid, assignment, family and evidence identities from a freshly frozen canonical namespace.

## Evidence and Console boundary

The pilot may create signed, append-only records only in a dedicated pilot evidence namespace. It may not append to the canonical Discovery evidence population.

Every Console surface must display a persistent banner:

`PILOT_ONLY · NON_PROMOTABLE · TIME_GATED_REPLAY · GAPPED_SOURCE`

Pilot candidates and clusters must not appear in canonical Discovery counts, family counts, novelty rankings, release selectors or promotion queues.

## Prohibited use

June pilot outputs may not:

- enter canonical Discovery population counts;
- define or seed final trajectory families;
- preserve candidate, cluster, medoid or assignment IDs for canonical use;
- receive semantic, archetype, theory or family promotion;
- select thresholds, queue caps, cluster counts or distance weights from observed outcomes;
- activate novelty ranking;
- alter the active C2 release, formulas, selectors or source truth;
- become OPT-C or OPT-D evidence;
- consume Validation;
- be relabelled `LIVE_PROSPECTIVE`;
- influence probability, risk, exposure, trading or execution;
- grant autonomous processing or agent write authority;
- trigger R2 publication or canonical release creation.

## Pilot completion and final freeze

After the pilot, the programme must stop at `PD-G5P — Pilot Discovery Operations Acceptance`.

The gate packet must include:

- exact source, run, binding and signed-acceptance identities;
- pilot candidate, queue, cluster, medoid and assignment counts;
- excluded and unavailable records with reasons;
- queue-cap, batching and runtime evidence;
- deterministic rerun comparison;
- Console and operator-review findings;
- signed pilot-evidence inventory;
- defect and correction ledger;
- versioned final contracts, schemas, parameter packs and identity rules;
- unresolved warnings and rollback;
- exact reset procedure for canonical identities.

Only an operator `PASS` at `PD-G5P` may freeze the operating contract and permit the canonical 2021–2023 Discovery population run. `DEFER`, `BLOCK`, `QUARANTINE` or `SUPERSEDE` leaves canonical Discovery unavailable.

## Canonical reset rule

Before canonical Discovery:

1. close and seal the pilot namespace;
2. prohibit any pilot ID from canonical import;
3. reset candidate, cluster, medoid, assignment, family and evidence sequences;
4. create a new immutable canonical identity salt or namespace version;
5. execute the 2021–2023 population from its exact source release with the final frozen contract;
6. keep all pilot records available only as operational QA lineage.

## Deferred genuine-live operation

`RPS-G4A` is superseded for the Pilot Discovery route. Genuine post-activation `LIVE_PROSPECTIVE` source intake and operation are reserved for a later separate operator gate, provisionally identified as `RPS-LIVE-G1`. No provider request or live operation is authorised by this contract.

## Rollback

Before pilot execution, rollback is a revert of the PD-G4B amendment decision and state records. After pilot execution, disable the pilot command, preserve all pilot outputs and signatures, mark the pilot `QUARANTINED` or `SUPERSEDED`, and prohibit reuse of its identities. Never delete, relabel or import pilot records into the canonical Discovery population.

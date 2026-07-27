# PD-G4B — Operator Decision

- Gate: `PD-G4B`
- Gate title: `Pilot Discovery Contract Amendment`
- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- Plan version: `0.1`
- Packet: `PD-WP5-PILOT`
- Baseline main: `0c177560b02e14a36a949626b155f616c12549e5`
- Gate-ready head: `33b227a632b9d19ce25b92abd5ef38485c73c7e5`
- Pull request: `#117`
- Operator command: `OVC APPROVE PD-G4B`
- Decision: `PASS`
- Decision authority: `OPERATOR`
- Approved on: `2026-07-27`

## Accepted amendment

The operator approves one bounded first PD-WP5 operation with the following immutable role and mode:

```yaml
research_role: PILOT_DISCOVERY
operation_mode: TIME_GATED_REPLAY
source: RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1
operation_limit: 1
pilot_only: true
promotion_eligibility: NON_PROMOTABLE
canonical_discovery_population: false
live_prospective: false
```

The operation is bound to:

- source manifest SHA-256 `429b7b568b7a43d04893c1873773f0b1b567730f2d5d4122d6a1c06dd40e3e41`;
- compute run `RPS.RUN.7aeb551335d766ee3bf503e6`;
- output manifest SHA-256 `3c6295badd04896a9e94b4b5a3ccb354bb51de52d5927839a86f61a40ed679ff`;
- source binding `RPS.BINDING.32fb3003efa072916c11e907`;
- signed replay acceptance `RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48`;
- signing binding `RPS.SIGNING.50092c28981fef08f53a6cb5`;
- operator `OVC.OPERATOR.PRIMARY.LOCAL.V1`;
- admissible cutoff `2026-06-25T00:00:00Z`.

No replacement source, compute run, signing identity, operator identity or provider request is authorised.

## Authority granted

This decision authorises a separate bounded implementation packet to:

1. implement and execute one operator-supervised Pilot Discovery rehearsal;
2. evaluate triggers and construct candidate windows from the exact accepted June chain;
3. exercise queue caps, suppression, merging, batching and backpressure;
4. construct deterministic fingerprints and provisional clusters;
5. generate pilot-only candidate, cluster, medoid and assignment identities;
6. project the pilot through the Research Console with a persistent pilot banner;
7. capture operator-signed append-only evidence only in the dedicated pilot namespace;
8. identify and correct versioned workflow, UI, queue, batching, missingness, manifest, identity, reproducibility and clustering-operational defects;
9. rerun deterministic checks after correctable in-scope changes;
10. prepare the consolidated `PD-G5P — Pilot Discovery Operations Acceptance` packet and stop there.

## Mandatory pilot isolation

Every pilot candidate, cluster, medoid, assignment, queue item, review decision, Console projection and evidence record must carry:

- `research_role = PILOT_DISCOVERY`;
- `operation_mode = TIME_GATED_REPLAY`;
- `pilot_only = true`;
- `promotion_eligibility = NON_PROMOTABLE`;
- `canonical_discovery_population = false`;
- `live_prospective = false`.

Pilot identities must remain under `PD.PILOT.GBPUSD.20260622_20260625.v1` or a deterministic child namespace. Before canonical 2021–2023 Discovery, candidate, cluster, medoid, assignment, family and evidence identities must be reset under a newly frozen canonical namespace.

## Authority not granted

This decision does not authorise:

- canonical 2021–2023 Discovery processing;
- inclusion of June outputs in canonical population or family counts;
- reuse of pilot identities in canonical Discovery;
- final trajectory-family definition;
- semantic, family, archetype or theory promotion;
- outcome-selected threshold, queue-cap, distance-weight or cluster-count tuning;
- active novelty ranking;
- C2 mutation, C2E, C2.5, C3, OPT-C or OPT-D;
- selector or release mutation;
- canonical or R2 publication;
- Validation consumption;
- probability, risk, exposure, trading or execution authority;
- autonomous processing or agent writes;
- provider access or a new source request;
- relabelling any pilot output as `LIVE_PROSPECTIVE`.

## RPS-G4A disposition

`RPS-G4A` is `SUPERSEDED_FOR_PILOT_DISCOVERY` only for the initial PD-WP5 operation. Its historical live-source blocker and evidence remain preserved. Genuine post-activation `LIVE_PROSPECTIVE` intake remains deferred to a separate future operator gate, provisionally `RPS-LIVE-G1`.

## Accepted evidence and QA

- Pilot amendment workflow `30307631723`, job `90115585496`: PASS.
- Historical live-blocker preservation and Pilot supersession workflow `30307631694`, job `90115585402`: PASS.
- Canonical repository workflow `30307631689`, job `90115585255`: PASS.
- QA recommendation: `PASS_RECOMMEND_OPERATOR_AMENDMENT`.
- Unresolved review threads: none.
- Blocking defects: none.

## Warnings accepted

1. The June source is `GAPPED`; missing or incomplete parents must remain excluded without interpolation or synthesis.
2. The short pilot cannot establish market, family or population conclusions.
3. Operational corrections must be versioned and may require a final contract change at PD-G5P.
4. Signed pilot evidence is operational QA lineage, not canonical Discovery evidence.
5. Pilot success establishes workflow readiness only.

## Rollback

Before pilot execution, revert the amendment and restore the prior RPS-G4A/live-blocker state. After any pilot output exists, preserve and seal or quarantine every pilot object and signature, prohibit canonical identity reuse and require a new operator decision before canonical Discovery. No rollback may delete or relabel append-only evidence.

## Continuation

1. Commit this operator decision and approved authority state.
2. Squash-merge PR `#117` into `main`.
3. Create a bounded `PD-WP5-PILOT` branch from the new lawful main tip.
4. Implement and execute the one approved rehearsal.
5. Correct in-scope operational defects and rerun affected tests.
6. Materialise the pilot review, final contract-freeze candidate and canonical identity-reset procedure.
7. Stop at `PD-G5P` for operator decision.

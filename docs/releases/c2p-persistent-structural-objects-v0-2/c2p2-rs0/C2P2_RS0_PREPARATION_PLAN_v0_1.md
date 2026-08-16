# C2P2-RS0 Preparation Plan v0.1

## Court-record identity

- programme_id: `OVC-C2P2-RS0-SHADOW-EVIDENCE-v0.1`
- parent_programme: `OVC-C2P2-OBJECTPACK-SCIENCE-v0.1`
- baseline_main: `1a3d1f399f9463166f1550416dd299f6002b0115`
- operator_decision: `PASS_COMPARATIVE_SET_TO_RS0_PREPARATION_ONLY`
- operator_constraints: `EC1_SCIENTIFIC_AUTHORITY_UNCHANGED`; `C2P_SHADOW_SIDECAR_ONLY`
- status: `PREPARATION_AUTHORISED / REAL_SOURCE_RUN_DENIED`

## Purpose

Prepare one strictly comparative, outcome-blind C2P shadow sidecar that can later evaluate the three PS0 ObjectPack candidates on one identical lawful source population. Preparation creates bindings, manifests, assurance requirements and a run-authority packet only. It does not execute C2P against real market data.

## Comparative candidate set

1. `C2P2-PS0-OP-A-STRICT-CONTINUITY-v1` — strict-control hypothesis.
2. `C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v1` — C2-only relational-continuity hypothesis.
3. `C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v1` — optional-C2E enrichment challenger.

All remain `activation_eligible=false`. There is no preferred/default winner and no scalar winner metric.

## Frozen source/population preparation envelope

RS0 is prepared against the existing EC1 Discovery source envelope only as a read-only sidecar population binding:

- instrument: `GBPUSD`
- sides: `BID`, `ASK` as separate identities
- clocks: `15M`, `2H_A_L`
- interval: `[2021-01-01T00:00:00Z, 2024-01-01T00:00:00Z)`
- research role: `DISCOVERY_SHADOW_ONLY`
- C2 source: current lawful C2 vNext active structural evidence for that exact release/population
- C2E source: current lawful C2E v0.2 evidence only where Candidate C declares it; optional by default and never sufficient alone for C2P identity
- OccurrenceContext: provenance/stratifier only; not C2P identity
- Validation: `LOCKED_UNCONSUMED`

The exact immutable upstream release IDs/hashes must be re-resolved immediately before any later run-authority decision. A changed release identity creates a new RS0 run generation rather than silent rebinding.

## EC1 firewall

RS0 has `scientific_effect=NONE` on EC1. C2P outputs may not:

- alter EC1 Q01-Q10 definitions, populations, denominators or search lattice;
- seed, filter, rank, freeze or promote EC1 Path-1 candidates;
- change the active EC1 evidence spine;
- create C2P as an EC1 candidate-defining source;
- consume OPT-C, OPT-D, Validation or future outcomes.

RS0 may later be inspected independently as architecture/capability evidence and may inform a separately governed future cycle or RV stack-sufficiency discussion only through an explicit owner-authorised handoff.

## Comparison constitution

Every candidate must receive the same source population, cutoff schedule, missingness policy, continuity segments, environment, checkpoint policy and physical resource envelope. Report candidate-specific and pairwise disagreement evidence separately. Required outputs include candidate/tracklet/assertion counts, ambiguity and not-evaluable denominators, censoring, dormancy/reappearance, retirement/recurrence, split/merge, cross-candidate correspondence, disagreement cases, Candidate-C optional-C2E delta, runtime/memory/storage/checkpoint evidence and exact replay equivalence.

No aggregate score or automatic winner is permitted.

## Resource and capacity envelope

Preparation freezes the semantic capacity policy now and defers numeric execution budgeting until the run-authority packet can cite reproducible dry-run/calibration evidence:

- identity-bearing computation: no sampling, reduced precision or semantic weakening;
- capacity exhaustion: fail closed with `CAPACITY_EXCEEDED` and preserved partial evidence;
- checkpoint/restart: logical result equivalence required;
- deterministic sharding: permitted only when recombination preserves exact logical identity;
- parent C2P reference-proof safety limits remain binding where applicable;
- numeric RS0 wall-clock/memory/storage/concurrency/checkpoint budget: `PENDING_MEASURED_FREEZE_BEFORE_REAL_SOURCE_RUN`.

No real-source run may begin while the numeric resource budget is unresolved.

## Required preparation artifacts

- `C2P2_RS0_SOURCE_POPULATION_BINDING_v0_1.json`
- `C2P2_RS0_PROGRAMME_STATE_v0_1.json`
- `C2P2_RS0_RUN_AUTHORITY_PACKET_v0_1.json`
- blocking authority/interlock tests

## Mandatory stop

Stop at `C2P2-RS0-GRUN` after preparation integration. That gate is operator-required and may authorize only the exact preregistered real-source shadow run. It cannot activate C2P, select an ObjectPack, change EC1 scientific authority, consume Validation, publish canon/R2, or create probability/risk/exposure/execution authority.

## Rollback

Forward-supersede RS0 preparation records only. Preserve PS0 candidates, operator decision, all negative evidence and parent C2P history. No force-push/history rewrite.

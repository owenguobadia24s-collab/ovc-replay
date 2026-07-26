# RO-WP1 — Evidence envelope and record schemas

## Result

`IMPLEMENTED — READY FOR RO-G1 OPERATOR REVIEW`

## Baseline

- Repository: `owenguobadia24s-collab/ovc-replay`
- Baseline: `8a4852358324a4e6dfc9f7c239be9e9eb8d69c23`
- Predecessor: `RO-G0 PASS`
- Validation: `LOCKED_UNCONSUMED`

## Implemented

- Research Operations authority boundary;
- permanent, model-optional evidence envelope;
- canonical UTF-8 JSON serialization;
- deterministic content-derived record IDs;
- ten research record types in one schema bundle;
- prospective cutoff enforcement;
- Validation metadata-only enforcement;
- DRAFT/FROZEN/ADJUDICATED/SUPERSEDED/WITHDRAWN lifecycle;
- freeze verification, duplicate-ID rejection and append-only supersession;
- explicit reproducibility states for missing artifacts;
- valid, leakage, mutation, missing, partial, locked and censored fixtures;
- executable evidence-integrity tests.

## Authority boundary

RO-WP1 creates pure code and governance records only. It creates no operator research record, durable write service, CLI, catalogue, QA runner, read model or console. RO-WP2 remains denied until a separate RO-G1 operator decision.

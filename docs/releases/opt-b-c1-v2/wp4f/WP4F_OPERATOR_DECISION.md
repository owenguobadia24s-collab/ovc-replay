# OPT-B.C1 v2 WP4F Operator Decision

## Decision

`PASS SUBJECT TO EXACT WORKFLOW VERIFICATION — DURABLE LOCAL RELEASE FREEZE`

WP4F consumes only the exact B1-G1 accepted candidate artifact `8626942276` and inventory SHA-256 `39f55e923fa0a8302024f02d862d294ad9d8448fe197a9849ee9ec0f15d4a383`.

The workflow creates immutable release roots for:

- `OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1`
- `OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1`

Each root contains the exact accepted record files, a release descriptor and a deterministic manifest. Every copied file is re-read and checked for exact size and SHA-256 before the release is accepted as `RELEASE_FROZEN / LOCAL_VERIFIED`.

## Retained authority boundary

- authority remains `CANDIDATE`;
- C1 selectors remain `NONE`;
- R2 publication remains denied pending a separate WP5 approval;
- Validation remains `LOCKED_UNCONSUMED`;
- C2 consumption remains denied pending a separate handoff review;
- probability, exposure, trading and execution authority remain `NONE`.

## Next gate

`OPT-B.C1 v2 B1-G2 — frozen release inventory and publication-readiness review`.

# RO2-00 — baseline and boundary freeze

## Status

`IN_PROGRESS — DESIGN RECORDS ONLY`

## Programme

- Programme: `OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.2`
- Work packet: `RO2-00`
- Branch: `design/research-operations-v0-2-bootstrap`
- Exact parent main commit: `85d2638d36c5039c35d2d49fcdb499dd48e7b354`
- Parent foundation: `OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.1`
- Parent authority: `RO-G3 PASS / ACTIVE_RESEARCH_OPERATIONS_LOCAL`

## Current-state reconciliation

The RO2-00 baseline is pinned after merge of C2-G4 exact-parent Discovery and Development replay.

C2-G4 is treated as completed bounded execution context with these retained facts:

- exact C1 and OPT-A parent chains passed full-byte verification;
- Discovery and Development replay completed;
- 404,434 state records and 323,910 transition records were produced externally;
- Validation remained `LOCKED_UNCONSUMED`;
- no C2 candidate release, publication, selector or activation authority was created;
- the next C2 boundary is candidate freeze and QA review.

The repository copies of `docs/CURRENT_STATUS.md` and `registries/authority/ACTIVE_AUTHORITY.yaml` predate the merged C2-G4 result. RO2-00 records this as a reconciliation dependency; this branch does not silently reinterpret or activate C2.

## Frozen construction boundary

Research Operations v0.2 extends v0.1 with five bounded, read-oriented capabilities:

1. role-workspace indexing;
2. observation indexing;
3. data-quality and bar-lineage inspection;
4. admissible-cutoff replay;
5. release/workspace comparison and Console v0.3 adapters.

The implementation remains additive inside `ovc-replay`. It does not create a parallel application or authority chain.

## Authority retained

- Market authority: `NONE`
- Validation consumption: `LOCKED_UNCONSUMED`
- C2 selector: `NONE`
- C2 activation: `NONE`
- Probability authority: `NONE`
- Exposure authority: `NONE`
- Trading authority: `NONE`
- Execution authority: `NONE`
- Autonomous-agent authority: `NONE`
- Direct UI writes to Git, R2, selectors, thresholds or releases: `DENIED`

Only the existing v0.1 append-only research-record service may freeze research records.

## Role-access freeze

| Operation | Discovery | Development | Validation |
|---|---|---|---|
| List approved release metadata | ALLOW | ALLOW | ALLOW |
| Resolve aggregate counts and manifest identity | ALLOW | ALLOW | ALLOW |
| Index observation rows | ALLOW | ALLOW | DENY |
| Inspect bar lineage | ALLOW | ALLOW | DENY |
| Prospective replay | ALLOW | ALLOW | DENY |
| Review replay | ALLOW | ALLOW | DENY |
| Create research session | ALLOW | ALLOW | DENY |

Validation denial must occur before external path resolution, object download or row access.

## One-way dependency freeze

```text
OPT-A sealed observations
  -> RO2 workspace and observation indexes
  -> quality, lineage, replay and diff projections
  -> Research Console v0.3 presentation
  -> optional v0.1 append-only research record service
```

No reverse writes are permitted. C1 and C2 attachments are optional, exact-release-bound read adapters. Missing optional model layers must produce `NOT_AVAILABLE` or `NOT_EVALUABLE`, never fabricated neutrality.

## Initial package boundary

```text
src/ovc/research_operations/v0_2/
  workspace_index/
  quality/
  lineage/
  replay/
  release_diff/
  console_adapters/
contracts/research_operations/v0_2/
schemas/research_operations/v0_2/
registries/research_operations/v0_2/
fixtures/research_operations/v0_2/
tests/research_operations/v0_2/
```

## Required RO2-G0 packet still to be constructed

- v0.2 authority contract;
- role-access policy;
- dependency allowlist and denylist;
- Console v0.3 workspace projection map;
- implementation and object registry;
- schema catalogue and identity rules;
- QA check-family registry;
- golden fixture matrix;
- baseline reconciliation packet with exact source hashes;
- operator decision and rollback record.

## Stop conditions

RO2 work must stop if any of the following occurs:

- prospective replay contains post-cutoff data;
- Validation content is resolved, downloaded or returned;
- an index cannot resolve exact source commit, release and manifest;
- accepted observations have orphan or cyclic lineage;
- a quality signal lacks exact evidence and consequence;
- an adapter writes to Git, R2, selectors, thresholds or releases;
- quarantined legacy ABCD code becomes an implementation dependency.

## Next authorised action

Continue RO2-00 on this branch by constructing the design-only contracts, registries, schema catalogue, fixture plan and RO2-G0 review packet. No runtime or live-data authority is granted by this record.

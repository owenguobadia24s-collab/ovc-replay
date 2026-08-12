# RCN vNext / OPT-B ESL PVS v0.2 — Phase 3 Investigate / G4 Preparation Plan v0.1

Status: OPERATOR_DIRECTED
Date: 2026-08-12
Programme: `OVC-RC-VNEXT-GREENFIELD-v0.1`
Governing plan: `OVC-RCN-RESEARCH-NATIVE-IMPLEMENTATION-PLAN-0.3-RATIFIED`
Phase: `PVS3`
Baseline main: `eed45f432f6661431fc546fc365aa3f043092697`
Branch: `build/rc-vnext-phase3-wp4d-refresh`
Authority delta before G4: `NONE`

## Purpose

Continue from completed PVS2 presentation conformance into the next lawful Research Console packet boundary. Phase 3 is limited to completing `RCN-RN-WP4D` fixture-only C3 owner-absence preparation on current main, reconciling WP4A-D preparation, and materialising one consolidated operator-required `RCN-RN-G4` decision packet.

Phase 3 does **not** itself grant G4. The first newly exposed real-source Investigate presentation remains operator-reserved.

## Court-record preflight

- Current lawful main at Phase 3 admission: `eed45f432f6661431fc546fc365aa3f043092697`.
- PVS2 is terminal/completed on main.
- RCN-RN state remains `RCN-RN-WP4C COMPLETED`, next packet `RCN-RN-WP4D_PREPARATION`.
- Historical PR #611 contains a previously passing WP4D preparation candidate but is stale/non-mergeable against current main; it is reference evidence only and will be superseded non-destructively.
- Current source census still records `OPT-B.C3` as `repository_materialized=false`, `source_path=null`, `TYPED_DEGRADED_STATE`, reason `UPSTREAM_OWNER_NOT_MATERIALIZED_AS_RUNTIME_NAMESPACE`.

## Phase 3 packets

### PVS3-WP0 — admission and stale-packet reconciliation
Materialise this phase record, pin current main, preserve PR #611 as historical preparation evidence, and move the RCN-RN machine state to fresh WP4D preparation.

### RCN-RN-WP4D — C3 typed owner-absence preparation refresh
On current main only:
- add GET-only `/api/v1/c3/graph`;
- expose only typed fixture absence for C3;
- bind schema, route registry, fixture manifest and OpenAPI snapshot;
- prohibit semantic synthesis and lower-layer substitution;
- preserve Validation denial before resource resolution;
- run targeted, Research Console, repository and stable-main assurance.

WP4D is auto-ratifiable only while authority delta remains `NONE`, QA recommends PASS, and no new real/semantic source is exposed.

### RCN-RN-G4 — consolidated operator decision packet
After WP4D merges and all WP4A-D preparation is complete, create one decision packet containing:
- exact current main and completed WP4 merge identities;
- source census and lawful candidate real-source bindings;
- current authority and proposed read-only source-presentation delta;
- acceptance conditions and invariants;
- tests/QA/warnings/unresolved issues;
- changed files and external artifact identities where applicable;
- rollback;
- recommended decision and exact work after approval.

Then stop. Allowed operator decisions: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`.

## Explicit exclusions

Before G4 PASS, Phase 3 may not:
- expose or resolve a new real market/scientific source through the console;
- activate or promote C2/C2E/C2P/C2.5/C3 semantics, selectors, thresholds, families, ObjectPacks, event vocabularies or grammar;
- access Validation or protected source details;
- add POST/PUT/PATCH/DELETE or any governance/write surface;
- publish canonically or to R2;
- add probability, risk, exposure, trading, execution or agent-write authority.

## G4 invariants

- C2 remains usable when C2E is unavailable; the console does not reconstruct episodes.
- C2P tracklets are not canonical downstream referents and ambiguity is not UI-resolved by nearest distance.
- C2.5 Candidate is not EventOccurrence; CENSORED is not TERMINATED; bounded open absence remains PENDING until closure/coverage proof.
- C3 graph connectivity is not entailment; temporal order is not causal order; conflicts have no UI-selected winner; renderer failure cannot alter AST truth.

## Rollback

Before WP4D merge, close the refresh PR and retain current main. After WP4D merge, revert only the preparation surface through a normal forward commit. In all cases preserve historical PR #611 evidence, PVS2 evidence and all scientific/authority state. No force-push or history rewrite.

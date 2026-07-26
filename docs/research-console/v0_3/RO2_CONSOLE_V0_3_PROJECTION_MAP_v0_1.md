# RO2 to Research Console v0.3 projection map

Status: `FROZEN_DESIGN_ONLY`
Gate: `RO2-G0`

## Boundary

This map defines how future RO2 typed objects may be projected into the accepted Console v0.3 shell. It creates no adapter, query, replay or write path. The Research workspace remains fixture-only until a later accepted gate.

## Context-preserving projection

| Console surface | RO2 source objects | Required presentation | Fail-closed state |
|---|---|---|---|
| Global context bar | RoleWorkspaceRef | role, release, manifest hash, source commit, clock, side, selected time | SOURCE_NOT_AVAILABLE |
| Research workspace summary | ConsoleResearchProjection, QualitySignal | authority, data freshness, selected role, counts, known limitations | NOT_EVALUABLE |
| Replay panel | ReplayFrame, ObservationRef | prospective/review mode, cutoff, visible IDs, hidden post-cutoff count | REPLAY_NOT_AVAILABLE |
| State and model attachment panel | OptionalModelAttachment | C1/C2 release and manifest, record refs, attachment status | MODEL_NOT_AVAILABLE |
| Lineage panel | BarLineageRecord | parent chain, first-valid times, source hashes, lineage status | LINEAGE_INCOMPLETE |
| Evidence panel | ObservationRef, existing v0.1 research records | exact immutable IDs and source authority | NO_EVIDENCE_MATERIALISED |
| Quality panel | QualitySignal | domain, evidence, freshness, consequence and affected surfaces | SIGNAL_NOT_EVALUABLE |
| Release comparison panel | ReleaseComparison | base/target identities, declared dimensions, differences and exclusions | COMPARISON_NOT_AVAILABLE |
| Research queue | existing v0.1 append-only service only | open sessions, due realisations, incidents and unresolved records | QUEUE_UNAVAILABLE |

## Role treatment

- Discovery and Development may later populate read-only Research, Replay, Evidence and Quality panels after their implementation gates.
- Validation may populate only release identity, aggregate inventory and a visible `LOCKED_UNCONSUMED` badge.
- Validation content must never be resolved to build a panel, preview, count-by-row, search index or cache.

## Interaction rules

- Every panel exposes source commit, release, manifest and authority.
- Prospective mode excludes post-cutoff records from both visible data and form inputs.
- Review mode labels all post-cutoff information explicitly.
- Missing C1/C2 attachments do not suppress OPT-A observations; they produce an unavailable state.
- No Console control writes to Git, R2, selectors, releases, parameters or thresholds.
- Any bounded research-record action routes only through the already accepted v0.1 append-only service.

# RO2 to Research Console v0.3 projection map

Status: `ACCEPTED_RO2_G3_ACTIVE_BOUNDED_LOCAL_READ_ONLY_PRESENTATION`
Gate: `RO2-G3`

## Boundary

This map defines the accepted read-only adapter boundary from accepted RO2-G1 and RO2-G2 typed objects into the Console v0.3 Research workspace. It creates no write path, selector authority, release authority or Validation-content access.

## Context-preserving projection

| Console surface | RO2 source objects | Required presentation | Fail-closed state |
|---|---|---|---|
| Global context bar | RoleWorkspaceRef | role, release, manifest hash, source commit, clock, side, selected time | SOURCE_NOT_AVAILABLE |
| Research workspace summary | ConsoleResearchProjection, QualitySignal | authority, selected role, counts, limitations | NOT_EVALUABLE |
| Replay panel | ReplayFrame, ObservationRef | prospective cutoff, visible IDs, hidden post-cutoff count | REPLAY_NOT_AVAILABLE |
| Lineage panel | BarLineageRecord | parent chain, source hashes and lineage status | LINEAGE_INCOMPLETE |
| Quality panel | QualitySignal | status, duplicate IDs and missing required fields | SIGNAL_NOT_EVALUABLE |
| Release comparison panel | ReleaseComparison | base/target identities, dimensions, differences and canonical identity | COMPARISON_NOT_AVAILABLE |

## Role treatment

- Discovery and Development populate read-only workspace, quality, lineage, replay and comparison panels.
- Validation exposes only release identity, manifest identity, aggregate inventory and a visible `LOCKED_UNCONSUMED` badge.
- Validation content, paths, timestamps, object identities and rows are denied before resolution.

## Interaction rules

- Every panel is deterministic and exposes a stable projection identity.
- Prospective replay excludes post-cutoff records and suppresses their identifiers, exposing only the hidden count.
- Missing source projections fail closed and do not create synthetic evidence.
- No Console control writes to Git, R2, selectors, releases, parameters, classifications or thresholds.
- No probability, exposure, trading, execution or autonomous-agent authority is introduced.
- Console projections are replaceable and never outrank their source releases, manifests, observations or RO2 read models.

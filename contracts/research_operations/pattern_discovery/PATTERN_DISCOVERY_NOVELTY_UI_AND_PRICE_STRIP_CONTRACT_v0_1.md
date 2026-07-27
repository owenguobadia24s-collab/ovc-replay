# Pattern Discovery Novelty, UI and Price-Strip Contract v0.1

## Novelty lifecycle

`BASELINE_FORMING -> CALIBRATED_SHADOW -> ACTIVE_NOVELTY_RANKING`

### BASELINE_FORMING

- Show prior signature counts and raw nearest-neighbour distance.
- Do not show LOW/MEDIUM/HIGH novelty badges.
- Novelty contributes no ranking weight and cannot independently promote a candidate.

Minimum burn-in:

- 60 completed valid candidate windows;
- 12 valid controls;
- 10 eligible operating days;
- more than one declared market condition;
- no unresolved critical lineage or leakage incident.

An eligible operating day requires available source release, healthy Pattern Discovery processing, an eligible market session and no critical incident. Holidays and stopped operation do not count.

### CALIBRATED_SHADOW

- Compute percentile and cluster-normalized novelty bands.
- Display badges marked `SHADOW`.
- Display the hypothetical rank impact.
- Do not change actual queue order and do not independently promote candidates.
- Accumulate at least 20 additional shadow-evaluated candidates and operator-disagreement metrics.

### ACTIVE_NOVELTY_RANKING

Requires an explicit operator gate after burn-in and shadow review. Novelty may contribute only its registry-declared bounded rank weight and remains subordinate to quality, incident and backpressure rules.

## Novelty definitions

- Signature novelty: `unseen_signature`, prior count and prior eligible frequency.
- Distance novelty before clusters: nearest-neighbour distance percentile against the burn-in distribution.
- Distance novelty after stable clusters: nearest-medoid distance divided by `max(cluster_p90_within_distance, epsilon)`.
- Initial bands after clustering: LOW `<1.0`; MEDIUM `1.0..1.5`; HIGH `>1.5`.
- Combination novelty: frequency of transition grammar + parent context + closure class.
- Temporal novelty: elapsed eligible time and candidate count since last occurrence.
- Conflict novelty: new cross-scale or level-relation conflict signature.

No opaque global interest score is canonical.

## Simple UI

The v0.1 local Streamlit surface has exactly three primary views:

1. `Queue`
2. `Candidate Detail`
3. `Clusters`

Visible buttons are authoritative. Optional browser-tested modifier shortcuts are disabled while any input, select or text area has focus. Batch actions are limited to dismiss with reason, defer, mark an already identified control and acknowledge stale items. Batch evidence creation is prohibited.

### Queue

Show release/commit/mode/freshness, filters, candidate window, trigger reason, compact transition summary, novelty dimensions, nearest cluster, quality, control status and queue age.

### Candidate Detail

Always visible: authority/source strip, compact price strip, trigger explanation, state-transition timeline, nearest-cluster summary and review actions.

Collapsed by default: full lineage, complete fingerprint, all neighbours, quality diagnostics and algorithm/configuration versions.

### Clusters

Show immutable cluster version, status, member count, medoid, dispersion, temporal/clock coverage, shared transition grammar, outliers, controls and limitations. Human actions may flag assignment, propose split/merge, restrict, reject or create an archetype proposal. They cannot promote semantics.

## Price-strip contract

- Source: exact canonical OPT-A bar release referenced by candidate C2 lineage.
- C1 is not a visual price source.
- Primary resolution: candidate C2 clock.
- Optional 15M detail beneath a 2H candidate requires exact cross-clock lineage.
- Markers: window start, trigger first-valid time, closure time and closure reason.
- Boundary references: exact C2 level/container records only; UI never recomputes them.
- Open windows refresh only after a newly eligible closed bar.
- Closed candidates are static.
- The strip must never show a bar newer than the represented C2 projection.
- Missing source or boundary lineage yields `NOT_AVAILABLE_SOURCE_UNRESOLVED`; no external-feed fallback.
- No drawing tools, indicators, trade annotations or embedded replay engine.

## PD-G4 efficiency targets

- Median dismiss/defer: <=45 seconds.
- Median control classification: <=45 seconds.
- Median full evidence review: <=3 minutes.
- Manual canonical source-ID entry: 0.
- Irrecoverable mis-clicks: 0.
- Failed source resolution: explicitly surfaced and never bypassed.

The gate packet may recommend revised targets after measured fixture use, but it may not silently weaken them.
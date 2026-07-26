# C2 Prospective Evidence Accumulation Contract v0.1

## Purpose

This contract governs prospective evidence accumulated under `RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1` after C2-G6 opened the line.

## Authority boundary

The only active research selector is the exact remote-verified C2 Discovery release `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`. The Development release is reference-only. Validation remains `LOCKED_UNCONSUMED`.

WP7 authorises append-only research records only. It does not authorise selector changes, release mutation, R2 mutation, threshold changes, probability claims, exposure decisions, trading or execution.

## Prospective cutoff

A record is admissible only when its observation timestamp and record creation timestamp are strictly later than activation commit `2a3f262fc0539786b67ae6c3e20604eb4d4adc2b` and after the C2-G6 opening transaction merged as `35c259255f4b09aca85de8bf114a6e1031b99e52`.

Historical material may be cited as context but cannot increment prospective evidence counts.

## Admissible record classes

- `STATE_FIDELITY_REVIEW`
- `BOUNDARY_CONFLICT_CASE`
- `ANOMALY`
- `INCIDENT`
- `BOUNDED_RESEARCH_QUESTION`

Each record must bind the research line, exact active release and manifest, canonical clock, price side, observation interval, source-object identity, deterministic record ID, author, creation timestamp and evidence status.

## Evidence status

New records begin as `OBSERVED_UNREVIEWED`. Permitted later states are `REVIEWED_ACCEPTED`, `REVIEWED_REJECTED`, `DUPLICATE_SUPERSEDED` and `INCIDENT_BLOCKED`. Status transitions must be append-only; prior rows are never rewritten.

## Prohibited seed material

The old 202-story programme, old 58-candidate programme, B-STATE-0.3b cases or labels, C2E episodes, C2.5 events, C3 meanings and historical OPT-C/OPT-D outputs cannot seed or count as WP7 evidence.

## Fail-closed rules

Unknown record classes, missing lineage, pre-cutoff observations, Validation references, prohibited imports, duplicate active record IDs, unresolved selector identity or any trading/execution field cause rejection.

## C2E escalation

WP7 may record sequence-boundary friction as evidence. It grants no C2E authority. A C2E proposal requires a separate gate supported by repeated, reproducible and independently reviewed friction records.
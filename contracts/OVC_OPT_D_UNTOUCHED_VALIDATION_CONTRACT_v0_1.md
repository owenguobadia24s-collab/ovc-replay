# OVC OPT-D Untouched Structural Validation Contract v0.1

**Contract ID:** `OPT-D-VALIDATE-0.1`  
**Parents:** `OPT-D-REVIEW-0.1`, `OPT-D-STORY-0.1`, `OPT-C-MEASURE-0.1`  
**Authority:** structural holdout validation only

## Frozen input boundary

The complete ratified 202-hypothesis batch is evaluated on one new sealed,
non-overlapping OPT-A release. The holdout may not change event definitions,
term thresholds, state semantics, path measurements, story fields, candidate
membership or validation thresholds. Any such drift invalidates the release.

The 2025 GBP/USD 15M series is the sole holdout story authority. M1-derived 2H
records may provide the already-ratified context and cross-clock overlap
lineage, but they receive no 2H hypothesis authority.

## Frozen antecedent and response

An antecedent match requires exact equality of event clock, broad event-family
set and event direction. Eligibility is determined at the event anchor close.

An exact response match requires equality of all seven forward fields:

- horizon;
- endpoint alignment;
- excursion dominance;
- first extreme;
- continuation state;
- primary-frontier outcome;
- endpoint range third.

No numeric return, excursion magnitude, semantic subcomponent or endpoint
B-state field may be substituted into either definition.

## Coverage and cluster counting

Only `COMPLETE` strict OPT-C paths receive neutral outcomes. Every censored path
remains visible in the coverage audit and is excluded without repair. The 24h
horizon remains coverage-only and 48h remains blocked.

Overlap clusters use the frozen OPT-D interval rule and are constructed per
horizon across both clocks. Hypothesis support is counted only by distinct
overlap-cluster ID; row counts are descriptive lineage and never substitute for
cluster counts.

All twelve supplied months are reported, including zero-support months.

## Frozen decisions

- `EVALUABLE`: at least 10 antecedent clusters across at least four months.
- `STRUCTURAL_STORY_REAPPEARED`: an evaluable hypothesis with at least 10 exact
  matching clusters across at least four months.
- `STRUCTURAL_STORY_NOT_REAPPEARED`: evaluable but below either reappearance
  threshold.
- `NOT_EVALUABLE_INSUFFICIENT_ANTECEDENT_COVERAGE`: below either evaluability
  threshold; this is not a failed hypothesis.
- Counter-story alert: for an evaluable hypothesis, contradictory response
  clusters are greater than or equal to exact matching clusters.

A contradictory response shares the exact antecedent and horizon and has
opposite endpoint alignment and/or opposite held-versus-lost frontier polarity.

## Authority boundary

Structural reappearance is not probability, independence, predictive edge,
recommendation, risk, trade or execution evidence. This release cannot activate
an execution path or authorize threshold selection.

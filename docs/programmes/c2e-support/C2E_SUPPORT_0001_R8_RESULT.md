# C2E-SUPPORT-0001 R8 — Shadow Successor Counterfactual Replay Result

## Decision

`PASS`

Verdict:

`SHADOW_EQUIVALENT_ON_EVALUABLE_CONTINUATIONS`

Authority delta: **NONE**.

Generation:

`C2E-SHADOW-G2A-ANCESTRY-PREREQ-v0.1`

## Discovery

```text
G1 continuation edges        532
Shadow supported             531
Shadow NOT_EVALUABLE           1
Shadow blocked                 0
Evaluable divergence           0

MAP survival                 531
Replacement support          135
Replacement-only               0
Relation Y / NE / N          531 / 0 / 1
```

## Source-pinned H11-H20 aggregate

```text
G1 continuation edges        181
Shadow supported             171
Shadow NOT_EVALUABLE          10
Shadow blocked                0
Evaluable divergence           0

MAP survival                 168
Replacement support           49
Replacement-only               3
Relation Y / NE / N          168 / 0 / 13
```

All ten R7 fingerprints reproduced through the R8 mechanical gate.

## Combined counterfactual result

```text
G1 continuation edges        713
Shadow supported             702
Shadow NOT_EVALUABLE          11
Shadow blocked                 0
Evaluable divergence           0

MAP survival                 699
Replacement support          184
Replacement-only               3
Relation Y / NE / N          699 / 0 / 14
```

## Scientific interpretation

The candidate ancestry prerequisite is observationally compatible with every ancestry-evaluable frozen-G1 continuation tested in discovery and the fresh source-pinned holdout.

No tested evaluable G1 continuation would be blocked by the candidate rule.

The three H11/H13/H18 replacement-only edges remain important because they show the candidate rule is not reducible to simple live-map overlap.

## Critical limitation

R8 observed:

```text
G1 boundary edges = 0
```

Therefore R8 does **not** establish boundary discrimination, specificity, termination value, or that the rule should become active.

The correct claim is:

> The candidate ancestry rule survives a false-negative / compatibility challenge against observed G1 continuations.

The unsupported stronger claim is:

> The rule has been shown to distinguish continuation from episode termination.

That remains untested.

## Next packet

`C2E-SUPPORT-0001 R9 — Boundary and Negative-Control Discrimination Challenge`

R9 remains inactive/shadow and does not change G1.

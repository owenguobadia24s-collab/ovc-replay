# OVC OPT-D Robustness Review Contract v0.1

**Contract ID:** `OPT-D-ROBUSTNESS-0.1`  
**Authority:** descriptive structural robustness review only  
**Probability, edge, trade and execution authority:** `NONE`

## Frozen input

The review binds the ratified 202-hypothesis batch and the sealed `OPT-D-VALIDATE-0.1` ledger for the non-overlapping 2025 GBP/USD holdout. It may not change an antecedent, response field, horizon, cluster definition, support threshold or counter-story rule.

## Diagnostics

For each frozen hypothesis the review reports:

1. exact leave-one-calendar-month-out recomputation across all twelve holdout months;
2. frozen-threshold margins and discovery-to-holdout structural support;
3. matching-cluster concentration using overlap clusters as the primary unit;
4. strict-path coverage and censoring exposure by month;
5. directional-mirror context where the frozen review batch contains a mirror; and
6. persistence of the preregistered counter-story alert under every month deletion.

A month-deletion test removes outcome rows by anchor month and then rebuilds distinct cluster sets from the remaining rows. Monthly summary counts are not subtracted, because a deterministic overlap cluster may span a month boundary.

## Interpretation

These diagnostics may add a conservative blocker or deferral. They may never turn a failed untouched-validation result into a pass, select a favorable month, optimize a threshold or establish row independence. A repeated qualitative story remains non-discriminating whenever its frozen contradictory-response cluster count equals or exceeds its matching cluster count.

No output is a probability estimate, predictive edge, recommendation, risk model, trading rule or execution instruction.

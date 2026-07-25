# OVC OPT-D-VALIDATE-0.1 Decision Note — GBP/USD 2025

**Validation status:** `PASS`  
**Holdout:** `OPT-A.GBPUSD.2025.v1`  
**Validated manifest:** `0411c0c45f5edcb1c83927ddc38be29064114778bd4a430f49fcd15221bcba75`

## Decision

Close the 202-hypothesis batch as **structurally recurrent but not
discriminating under the frozen counter-story rule**.

- All 202 hypotheses were evaluable.
- 197 met the frozen structural-reappearance threshold.
- Five did not reappear.
- All 202 triggered the preregistered counter-story alert.
- Across hypotheses, contradictory-cluster support was at least 1.61 times
  exact-match support; the median ratio was 6.17.

Structural recurrence therefore does not authorize promotion of any hypothesis
to probability, predictive edge, recommendation, trade, production, risk or
execution status.

## Research boundary

The 2025 release is no longer untouched and must not be reused as a future
holdout. Any attempt to improve discrimination—such as a more specific
antecedent, a different response partition or a revised counter-story rule—must
start a separately versioned exploratory cycle and be validated on another new
sealed non-overlapping release. The frozen 0.1 validation result must remain
unchanged.

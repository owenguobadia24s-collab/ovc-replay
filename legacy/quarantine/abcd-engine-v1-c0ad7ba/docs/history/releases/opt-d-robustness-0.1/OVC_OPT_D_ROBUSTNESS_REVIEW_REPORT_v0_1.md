# OVC OPT-D Robustness Review v0.1

**Status:** `ROBUSTNESS_REVIEW_COMPLETE_NO_PROMOTION_AUTHORITY`  
**Contract:** `OPT-D-ROBUSTNESS-0.1`  
**Probability / edge / paper-playbook / execution authority:** `NONE`

## Result

All **202** frozen hypotheses were recomputed under twelve exact leave-one-month-out deletions. Baseline recurrence survived every month deletion for **187** hypotheses. The preregistered counter-story alert survived every month deletion for **202** hypotheses.

| Horizon | Total | Baseline reappeared | LOMO-stable | Counter alert | Counter alert LOMO-persistent |
|---:|---:|---:|---:|---:|---:|
| 1h | 62 | 62 | 58 | 62 | 62 |
| 2h | 61 | 61 | 57 | 61 | 61 |
| 4h | 50 | 48 | 48 | 50 | 50 |
| 8h | 29 | 26 | 24 | 29 | 29 |

## Directional context

The frozen batch contains **78** complete UP/DOWN mirror pairs and **46** unpaired hypotheses. Directional agreement is reported only as context; mirror absence is not used to invent or discard a hypothesis.

## Interpretation boundary

The review confirms whether the structural result depends on any single holdout month. It does not estimate probability or edge. Counter-story persistence means distinct overlap clusters repeatedly express a response that satisfies the preregistered contradiction rule for the same antecedent and horizon. A robustness diagnostic can add a blocker or deferral but cannot rescue a frozen validation failure.

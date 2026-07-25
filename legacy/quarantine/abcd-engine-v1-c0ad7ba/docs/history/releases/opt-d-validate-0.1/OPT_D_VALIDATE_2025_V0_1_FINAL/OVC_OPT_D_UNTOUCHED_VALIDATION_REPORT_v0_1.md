# OVC OPT-D Untouched Structural Validation Report v0.1

**Status:** `UNTOUCHED_STRUCTURAL_VALIDATION_COMPLETE`  
**Contract:** `OPT-D-VALIDATE-0.1`  
**Probability / edge / trade / execution authority:** `NONE`

## Holdout boundary

- Holdout OPT-A seal: `OPT-A.GBPUSD.2025.v1`
- Holdout interval: `[2025-01-01T00:00:00Z, 2026-01-01T00:00:00Z)`
- Discovery interval: `[2026-01-01T00:00:00Z, 2026-07-01T00:00:00Z)`
- Temporal overlap: **none**
- Ratified hypotheses evaluated: **202**

## Frozen validation results

| Disposition | Hypotheses |
|---|---:|
| `NOT_REAPPEARED_WITH_COUNTER_STORY_ALERT` | 5 |
| `REAPPEARED_WITH_COUNTER_STORY_ALERT` | 197 |

Evaluable hypotheses: **202**. Structurally reappeared: **197**. Counter-story alerts: **202**.

## By horizon

| Horizon | Total | Evaluable | Reappeared | Counter alerts |
|---:|---:|---:|---:|---:|
| 1h | 62 | 62 | 62 | 62 |
| 2h | 61 | 61 | 61 | 61 |
| 4h | 50 | 50 | 48 | 50 |
| 8h | 29 | 29 | 26 | 29 |

## Interpretation boundary

A structural reappearance means only that the exact frozen qualitative story met the preregistered cluster/month threshold in the untouched year. A non-reappearance or counter-story alert is retained without threshold changes. None of these labels establishes independence, probability, predictive edge or a trading rule.

All contract-compliant censored paths remain in the OPT-C coverage audit and receive no outcome row. No missing path was repaired, and all twelve holdout months—including zero-support months—are represented in every hypothesis record.

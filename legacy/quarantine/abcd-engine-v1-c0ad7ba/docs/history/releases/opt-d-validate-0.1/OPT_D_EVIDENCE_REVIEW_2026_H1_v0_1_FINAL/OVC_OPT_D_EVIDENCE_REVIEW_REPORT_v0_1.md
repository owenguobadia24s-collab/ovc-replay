# OVC OPT-D Evidence Review and Pending Hypothesis Register v0.1

**Status:** `BUILT FOR OPERATOR RATIFICATION — NOT PREREGISTERED`  
**Contract:** `OPT-D-REVIEW-0.1`  
**Probability / edge / trade / execution authority:** `NONE`

## Outcome-neutral dispositions

| Disposition | Archetypes |
|---|---:|
| `CANDIDATE_FOR_BATCH_PREREGISTRATION` | 202 |
| `RETAIN_LIMITED_SUPPORT_INVENTORY` | 449 |
| `RETAIN_MINIMAL_SUPPORT_INVENTORY` | 309 |
| `RETAIN_SINGLETON_INVENTORY` | 870 |

Pending batch hypotheses: **202**. All are labelled in-sample exploratory. Admission used only the parent cluster-repetition label; endpoint alignment and H1 path direction were not selection inputs.

## Candidate composition

| Dimension | Counts |
|---|---|
| Clock | `15M` 202 |
| Horizon | `1h` 62, `2h` 61, `4h` 50, `8h` 29 |
| Direction | `DOWN` 104, `UP` 98 |
| Endpoint alignment | `ALIGNED` 81, `OPPOSITE` 121 |
| Discovery months | `4` 15, `5` 38, `6` 149 |

The register contains adverse and aligned paths together: selection is deliberately not a favourable-story filter.

## Directional symmetry review

- Candidates with an exact mirrored counterpart: **156**
- Complete directional pairs: **78**
- Candidates without an exact mirrored counterpart: **46**

Mirror absence is retained as review evidence. It is not repaired by weakening the story definition.

## Counter-story surface

- Candidates with a deterministic competing response: **202**
- Candidates without a qualifying competing response: **0**
- Per-candidate distinct counter-story cluster links, summed across records: **25,182**

A counter-story shares the event antecedent and horizon but reverses endpoint alignment and/or held-versus-lost frontier polarity.

## Clock boundary

All pending hypotheses are 15M. No 2H parent contrast reached the admitted OPT-D story surface, so this release grants no 2H story hypothesis authority.

## Frozen untouched-validation gate

A new non-overlapping sealed OPT-A release is required. A hypothesis is evaluable only with at least 10 antecedent clusters across four months, and structurally reappears only with at least 10 exact story matches across four months. Definition changes after opening holdout data invalidate the run.

## Operator decision

The contract and the complete candidate set remain pending batch ratification. No individual hypothesis may be selected because its H1 path appears favourable. After ratification, the next build is `OPT-D-VALIDATE-0.1` on untouched data.

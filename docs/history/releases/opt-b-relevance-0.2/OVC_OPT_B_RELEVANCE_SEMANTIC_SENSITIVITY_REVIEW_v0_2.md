# OVC OPT-B Level Relevance, Semantic and Threshold-Sensitivity Review

**Status:** `REVIEWED — OPERATOR RATIFICATION REQUIRED — NOT ACTIVE`  
**OPT-A seal:** `OPT-A.GBPUSD.2026H1.v1`  
**Relevance contract:** `B-REF-0.2`  
**Initial sensitivity seed:** `SEED_48H` (8-hour ranges, 48-hour swings)  
**Recommended next-replay policy:** `STRUCTURAL_ONLY`

## Relevance comparison

| Clock | Policy | Mean active levels | Max | Ambiguous bars | Ambiguous rate |
|---|---|---:|---:|---:|---:|
| 15M | NO_RETIREMENT | 5773.14 | 11488 | 6,922 | 58.51% |
| 15M | STRUCTURAL_ONLY | 3.83 | 15 | 991 | 8.38% |
| 15M | TIGHT_24H | 3.74 | 15 | 987 | 8.34% |
| 15M | SEED_48H | 3.74 | 15 | 987 | 8.34% |
| 15M | RELAXED_72H | 3.80 | 15 | 991 | 8.38% |
| 2H | NO_RETIREMENT | 750.80 | 1489 | 722 | 47.47% |
| 2H | STRUCTURAL_ONLY | 4.10 | 12 | 133 | 8.74% |
| 2H | TIGHT_24H | 2.82 | 7 | 109 | 7.17% |
| 2H | SEED_48H | 2.98 | 9 | 126 | 8.28% |
| 2H | RELAXED_72H | 3.31 | 9 | 126 | 8.28% |

## Semantic finding

The no-retirement baseline allows obsolete and current levels to claim the same bar. Relevance filtering tests whether ambiguity falls without using outcomes. Remaining ambiguity is preserved explicitly; no nearest-level or best-level heuristic is introduced.

Range supersession and acceptance-through account for nearly all useful
retirement. `STRUCTURAL_ONLY` leaves a mean 3.83 active levels at 15M and 4.10
at 2H, with only one and two levels respectively still active at the end of H1.
It therefore supplies the simplest coherent lifecycle without importing an
arbitrary age cutoff.

The TTL variants add little at 15M. At 2H, the 24-hour swing cap reduces the
reported ambiguity from 8.74% to 7.17%, but both 24-hour and 48-hour policies
produce 194 bars with no active reference. That is a semantic trade-off, not
evidence that the shorter cap is more correct.

### Ambiguity taxonomy

The current resolver treats distinct level IDs as distinct states, even when
their semantic label and direction agree. The review separates these cases:

| Clock | Policy | Coherent multi-level | Conflicting states | Conflict rate |
|---|---|---:|---:|---:|
| 15M | STRUCTURAL_ONLY | 600 | 391 | 3.31% |
| 15M | SEED_48H | 599 | 388 | 3.28% |
| 2H | STRUCTURAL_ONLY | 72 | 61 | 4.01% |
| 2H | SEED_48H | 67 | 59 | 3.88% |

A later state-contract revision should represent coherent agreement as a
compound state such as `ACCEPTED_BELOW {level_ids...}`. Only contradictory
semantic labels should remain `AMBIGUOUS`. This preserves every relevant level
without introducing nearest-level or hidden-best selection.

Acceptance dominates the retained state surface and also serves as a retirement
trigger. This is deterministic but definitionally coupled: operator review must
confirm that “accepted through” really means the prior level is no longer part
of the current story.

## Threshold finding

Compression and displacement sensitivity is measured over their full evaluated populations. Level-term sensitivity rechecks the observable distance predicates of seed-relevant confirmed episodes under conservative, seed and permissive profiles. These counts describe classification stability, not edge.

| Clock | Term | Conservative | Seed | Permissive |
|---|---|---:|---:|---:|
| 15M | Compression | 36 | 119 | 337 |
| 15M | Displacement | 311 | 505 | 823 |
| 2H | Compression | 3 | 8 | 34 |
| 2H | Displacement | 32 | 50 | 90 |

Compression is highly threshold-sensitive and remains provisional.
Displacement is more persistent but still changes materially across the profile
range. Neither threshold set should be changed or activated from this sample.

Among seed-relevant confirmed level episodes, the conservative distance profile
retains 89–99% depending on the term. Breach/response and rejection are the most
sensitive; acceptance is the most stable. Permissive entry bands expand the
candidate surface by roughly 3–7%, but additions require a full controlled
response-window replay before they may be treated as classifications.

## Recommendation

1. Carry `STRUCTURAL_ONLY` into the next deterministic replay.
2. Keep 8h/24h/48h/72h TTLs as research variants, not active rules.
3. Freeze the current `B-LANG-0.1-SEED` thresholds for comparability.
4. Revise state representation so coherent multi-level agreement is compound,
   while contradictory labels remain ambiguous.
5. Prioritize operator inspection of acceptance retirement and true conflicts.
6. Define the missing deterministic `NEUTRAL` exit before promoting transition
   semantics.

## Promotion boundary

`B-REF-0.2` trigger semantics and the `STRUCTURAL_ONLY` policy remain review
candidates. Operator ratification, a full response-window replay for any
threshold change, additional closed-period validation, and the missing
deterministic NEUTRAL exit contract remain mandatory before activation.

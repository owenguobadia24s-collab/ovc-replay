# OVC B-STATE-0.3 Parallel-Axis H1 Replay and v0.2 Comparison

**Status:** `CONTROLLED H1 REPLAY COMPLETE — B-STATE-0.3 NOT RATIFIED`  
**Relevance authority:** `B-REF-0.2-STRUCTURAL-ONLY`  
**Outcome use:** `NONE`

## Headline comparison

| Clock | v0.2 acceptance occupancy | v0.3 location occupancy | v0.2 ambiguity occupancy | v0.3 genuine conflict | v0.2 suppressed | v0.3 suppressed |
|---|---:|---:|---:|---:|---:|---:|
| 15M | 86.86% | 99.67% | 5.15% | 0.00% | 1,245 | 0 |
| 2H | 81.53% | 97.63% | 6.18% | 0.00% | 136 | 0 |

## Decisive semantic finding

Parallel axes solve the authority problem: acceptance no longer suppresses displacement, compression or interaction evidence, and topology-aware conflict does not mislabel different-level observations as contradictory. However, the proposed maintained-location rule creates a second saturation problem. Accepted-above lower levels and accepted-below higher levels accumulate into `ACCEPTED_CORRIDOR`, leaving the location axis active on nearly every H1 bar.

`B-STATE-0.3` therefore remains blocked from ratification. The next revision must either represent acceptance as a level-relation collection without a categorical corridor state, or close accepted-through relations under an explicitly bounded lifecycle. This decision must be tested semantically before any OPT-C outcome is introduced.

## State duration

Durations are contiguous-bar episodes and split at every source gap.

| Clock | Contract | Episode | Median bars | P90 bars | Maximum bars |
|---|---|---|---:|---:|---:|
| 15M | v0.2 | acceptance active | 11.0 | 30 | 93 |
| 15M | v0.3 | location active | 6.0 | 94 | 185 |
| 2H | v0.2 | acceptance active | 16.5 | 27 | 36 |
| 2H | v0.3 | location active | 59.0 | 60 | 60 |

## Transition frequency

v0.2 reports its one exclusive state stream. v0.3 reports each independent axis; these rates must not be summed as though they were one state machine.

| Clock | v0.2 exclusive | v0.3 location | displacement | compression | interaction | quality |
|---|---:|---:|---:|---:|---:|---:|
| 15M | 183.26 | 3.89 | 63.91 | 10.14 | 268.55 | 18.60 |
| 2H | 171.60 | 9.86 | 50.62 | 6.57 | 259.70 | 16.44 |

## Interpretation boundary

The comparison measures semantic behaviour only. It does not select v0.3 using returns, MFE/MAE, profitability or any OPT-C outcome. `B-STATE-0.3` remains a replayed candidate requiring operator review.

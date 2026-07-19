# OVC B-STATE-0.3a Acceptance Relation-Inventory H1 Replay

**Status:** `CONTROLLED H1 REPLAY COMPLETE — B-STATE-0.3a NOT RATIFIED`  
**Relevance authority:** `B-REF-0.2-STRUCTURAL-ONLY`  
**Outcome use:** `NONE`

## Representation comparison

| Clock | v0.2 persistent acceptance | v0.3 categorical location | v0.3a acceptance event | v0.3a relation inventory present |
|---|---:|---:|---:|---:|
| 15M | 86.86% | 99.67% | 28.59% | 99.67% |
| 2H | 81.53% | 97.63% | 24.98% | 97.63% |

The high relation-inventory presence is retained as an observable fact, but it no longer occupies or governs a categorical state. Only lawful new acceptance confirmations occupy the event field.

## Duration and transition comparison

| Clock | Model | Active median | Active P90 | Active max | Transitions / 1,000 bars |
|---|---|---:|---:|---:|---:|
| 15M | v0.2 persistent acceptance | 11.00 | 30.00 | 93 | 73.80 |
| 15M | v0.3 categorical location | 6.00 | 94.00 | 185 | 0.08 |
| 15M | v0.3a acceptance event | 1.00 | 3.00 | 7 | 382.50 |
| 2H | v0.2 persistent acceptance | 16.50 | 27.00 | 36 | 77.58 |
| 2H | v0.3 categorical location | 59.00 | 60.00 | 60 | 0.66 |
| 2H | v0.3a acceptance event | 1.00 | 3.00 | 4 | 347.80 |

Consecutive acceptance confirmations can form short event runs, but the event is recomputed from current-bar evidence and is never carried forward. The median active run is one bar on both clocks.

## Inventory measurements

| Clock | Median relations | P90 relations | Max relations | Median boundary width | P90 boundary width | Relation-set changes / 1,000 bars |
|---|---:|---:|---:|---:|---:|---:|
| 15M | 140.00 | 179.00 | 203 | 25.50 pips | 57.40 pips | 338.97 |
| 2H | 57.00 | 70.00 | 83 | 71.40 pips | 151.40 pips | 314.92 |

The inventory still contains old relations because the ratified structural-only policy has no elapsed-time expiry. This is disclosed rather than hidden: the oldest active relation reaches 10,177 observed 15M bars and 1,301 observed 2H bars. That is a relevance-inventory review issue, not categorical state dominance.

## Semantic controls

| Clock | Genuine conflict | Cross-axis suppression | Unchanged v0.3 axes match |
|---|---:|---:|---:|
| 15M | 0.00% | 0 | PASS |
| 2H | 0.00% | 0 | PASS |

## Interpretation boundary

v0.3a changes representation only. The acceptance classifier, level lifecycle, maintenance exits and all non-acceptance axes remain frozen. No OPT-C outcome, profitability, future bar, recommendation or execution input entered the replay.

**Review finding:** the semantic-dominance defect is removed from the categorical state model. Ratification should still require operator review of whether a fresh acceptance event rate near one bar in four is linguistically useful, and a separate future contract should decide how to summarize the large relation inventory without outcome-tuned pruning.

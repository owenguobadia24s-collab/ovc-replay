# PD-JUNE-MDR-WP1 — Claim-level Market-Description Review

## Scope

This packet reviews the exact June 22–25, 2026 GBP/USD Pilot Discovery v2 artifacts supplied by the operator. It does not run the market again and does not authorise the 2021–2023 canonical Discovery population.

## Exact evidence received

Seven predeclared hashes matched exactly: console bundle, queue items, candidates, fingerprints, trigger events, transitions and cluster versions. Five additional source/binding artifacts were hashed and inventoried now. Raw market data and large derived files remain outside Git.

All 208 candidate identities reconcile with 208 fingerprints and 208 trigger events. Every trigger transition link resolves into the 7,032-transition ledger. Every one of the 328 candidate timeline timestamps joins to a complete side-specific 15M source bar.

## Claim-level review set

- All six queue-promoted candidates.
- Twenty nonqueue candidates, selected deterministically as the lexicographically first candidate in every observed `(side, trigger reason, quality, parent containment)` stratum.
- No negative-control candidate exists in the 208-candidate population.

## Material findings

1. **Source binding conflict.** The uploaded prospective source binding names `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`; the reviewed candidates and console name v2.
2. **Timeline ordering failure.** Forty-four of 208 candidate timelines are serialized out of first-valid chronology, including four of six promoted candidates.
3. **Semantic evidence missing.** Exact C1 facts, level boundaries, relation values and formula inputs are absent, so raw OHLC cannot independently verify the displayed structural labels.
4. **Trigger history incomplete.** The exact pre-trigger histories required for `LONG_PERSISTENCE` and `REPEATED_SWITCHING` are absent.
5. **Structural comparison partial.** Medoids and total distances are present, but component distance decomposition is not generally exposed.
6. **No population reliability evidence.** No reviewed unit receives a full semantic-description `SUPPORTED` verdict, and no repeat-review agreement or negative-control rate exists.

## Result

- Mechanical artifact integrity: **PASS**
- Complete source bars at candidate timestamps: **PASS for observed windows**
- Serialized chronology: **FAIL**
- Source-to-C2-v2 binding: **FAIL**
- External market-description validity: **NOT ESTABLISHED**
- Population-level consistency: **NOT ESTABLISHED**

The recommended operator decision at `PD-JUNE-MDR-G1` is **DEFER**. The bounded successor would correct evidence binding and read-only presentation only. It would not change formulas, triggers, candidate rules, distances, clustering, thresholds, selectors, releases or market authority.

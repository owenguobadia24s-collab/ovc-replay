# OVC OPT-A Seal Record — GBP/USD 2026 H1

**Seal ID:** `OPT-A.GBPUSD.2026H1.v1`  
**Status:** `SEALED_RESEARCH_AUTHORITY`  
**Sealed:** 2026-07-19  
**Seal hash:** `0927f7a2b078d670370eb9ec26718f3e2ff0d97708df1f785a9333264415ef99`

## Bound authority

- Canonical 2H spine: provider H1 → two exact fixed-UTC H1 bars → 2H.
- Canonical 15M detail: provider-returned M1 → fifteen exact M1 records → 15M.
- No H1/2H object may fabricate M1 or 15M history.
- No absent minute is filled, flattened, inferred or silently repaired.
- Incomplete 15M buckets remain quarantined.
- The 209 canonical 2H bars without complete M1 detail are retained with `M1_DETAIL_INCOMPLETE` lineage.

## Counts

| Object | Count |
|---|---:|
| Raw provider M1 rows | 183,619 |
| Canonical 15M bars | 11,830 |
| Canonical 2H bars | 1,521 |
| 2H with complete M1 detail | 1,312 |
| 2H with incomplete M1 detail | 209 |
| Rejected H1-derived 2H buckets | 33 |
| Rejected M1-derived 15M buckets | 470 |

## Boundary

This seal authorizes immutable research input for OPT-B through OPT-D. It does not activate OPT-B language, establish edge, authorize paper/live execution, or supersede legacy `ovc-infra` operational authority. A byte change requires a new seal and version.

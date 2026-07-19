# OVC B-STATE-0.3b Acceptance Frontier Semantic Review

**Representation boundary:** `B-STATE-0.3a-REPRESENTATION-ONLY — RATIFIED`  
**Frontier candidate:** `B-STATE-0.3b-REVIEW — NOT RATIFIED`  
**Outcome use:** `NONE`

## Event-surface comparison

| Clock | Variant | Event occupancy | Active median | Active P90 | Active max | Active transitions / 1,000 bars |
|---|---|---:|---:|---:|---:|---:|
| 15M | Raw confirmation | 28.59% | 1.00 | 3.00 | 7 | 382.50 |
| 15M | Boundary confirmation | 15.11% | 1.00 | 2.00 | 5 | 244.55 |
| 15M | Outward frontier advance | 11.93% | 1.00 | 2.00 | 4 | 203.30 |
| 2H | Raw confirmation | 24.98% | 1.00 | 3.00 | 4 | 347.80 |
| 2H | Boundary confirmation | 12.89% | 1.00 | 2.00 | 4 | 212.36 |
| 2H | Outward frontier advance | 10.65% | 1.00 | 2.00 | 3 | 182.12 |

Raw confirmations remain auditable. Boundary confirmation removes interior-level repetitions. Frontier advance further requires the accepted floor to move higher or the accepted ceiling to move lower on a contiguous sealed bar.

## Evidence retention and composite occupancy

| Clock | Boundary retains raw | Frontier retains raw | Frontier retains boundary | Any-axis active with raw | Any-axis active with frontier |
|---|---:|---:|---:|---:|---:|
| 15M | 52.84% | 41.72% | 78.96% | 55.94% | 46.35% |
| 2H | 51.58% | 42.63% | 82.65% | 45.69% | 37.48% |

## Monthly event rates

| Clock | Month | Raw | Boundary | Frontier advance |
|---|---|---:|---:|---:|
| 15M | 2026-01 | 27.16% | 13.47% | 11.05% |
| 15M | 2026-02 | 27.73% | 15.14% | 11.57% |
| 15M | 2026-03 | 29.31% | 15.33% | 11.97% |
| 15M | 2026-04 | 29.53% | 16.19% | 12.75% |
| 15M | 2026-05 | 29.14% | 15.38% | 12.72% |
| 15M | 2026-06 | 28.54% | 15.08% | 11.49% |
| 2H | 2026-01 | 22.62% | 16.27% | 13.10% |
| 2H | 2026-02 | 22.50% | 10.83% | 10.42% |
| 2H | 2026-03 | 25.57% | 11.83% | 9.54% |
| 2H | 2026-04 | 30.00% | 15.00% | 11.92% |
| 2H | 2026-05 | 23.89% | 12.15% | 9.31% |
| 2H | 2026-06 | 25.00% | 11.15% | 9.62% |

## Inventory projection

| Clock | Canonical byte reduction | ID-reference reduction | Full ledger | Genuine conflict |
|---|---:|---:|---|---:|
| 15M | 93.65% | 97.96% | Preserved by parent hash | 0.00% |
| 2H | 85.89% | 95.35% | Preserved by parent hash | 0.00% |

The compact projection is a view, not a relevance filter. Every relation remains in the manifest-bound parent ledger; no TTL, rank, score or best-level selector was introduced.

## Recommendation

Adopt `FRONTIER_ADVANCE` as the next controlled state-timeline candidate. Keep `RAW_CONFIRMATION` as audit evidence and `BOUNDARY_CONFIRMATION` as a diagnostic. Use the compact frontier projection as the default review view while retaining the full relation inventory as machine authority.

This recommendation is semantic only. It does not ratify v0.3b or authorize outcome, edge, recommendation, production or execution use.

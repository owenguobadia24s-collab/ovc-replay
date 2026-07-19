# OVC OPT-A GBP/USD 2025 Validation Ingestion and Seal

**Status:** `SEALED 15M HOLDOUT RESEARCH AUTHORITY`  
**Seal ID:** `OPT-A.GBPUSD.2025.v1`  
**Execution authority:** `NONE`

## Provider release

- Interval: `[2025-01-01, 2026-01-01)` UTC
- Provider-returned GBP/USD BID minutes: 371,074
- Source SHA-256: `613abc547b5a53ac982c02ae68c4c3046c69a737cb70a080da3e058bc7cdf6ac`
- First provider minute: `2025-01-01T22:01:00+00:00`
- Last provider close: `2025-12-31T21:59:00+00:00`
- Synthetic flat minutes: `PROHIBITED / NOT REQUESTED`

## Strict coverage

- Absent interval minutes retained: 154,526
- Internal closure-like gaps: 53
- Internal sparse gaps: 1,500
- Boundary absences: 2
- Complete accepted 15M bars: 23,824
- Touched but incomplete 15M buckets quarantined: 1,076
- Contiguous 15M segments: 677

## Authority boundary

The complete 15M bars are the sole holdout story authority. The 2,633
complete minute-chain 2H bars are retained only as validation context and grant no
2H OPT-D hypothesis authority. Missing minutes, untouched buckets and incomplete
buckets were not filled, repaired or inferred. This holdout may not alter the
ratified H1 hypotheses or their thresholds.

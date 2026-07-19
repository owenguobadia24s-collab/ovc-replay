# Data boundary

This repository contains no OHLCV records or market-data CSVs. Raw provider
files, accepted bar tables, reconciliation ledgers, quality ledgers, and
generated replay streams are external dependencies bound by their release
manifests.

Rules inherited from OPT-A:

- normalize offset-aware timestamps to UTC;
- never fill or infer absent provider minutes;
- accept a 15M bucket only when all 15 one-minute bars are present;
- use provider H1 bars as the deterministic 2H authority where sealed;
- never reconstruct lower-resolution detail from H1 or 2H data;
- segment every downstream window at gaps and rejected buckets.

The 2026 H1 period is discovery evidence. Calendar year 2025 was the untouched
validation period and is now consumed evidence.

See [External dependencies](EXTERNAL_DEPENDENCIES.md) for the sealed dataset
identities and integrity hashes required to reproduce the historical releases.

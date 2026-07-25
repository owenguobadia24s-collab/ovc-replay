# OVC GBP/USD 2025 Ingestion and OPT-D-VALIDATE-0.1 Handover

## Provider release

- Instrument: `GBPUSD`
- Price side: `BID`
- Source clock: `1M`, UTC
- Interval: `[2025-01-01T00:00:00Z, 2026-01-01T00:00:00Z)`
- Provider-returned candles: `371,074`
- Synthetic flat candles: `0`
- Raw SHA-256: `613abc547b5a53ac982c02ae68c4c3046c69a737cb70a080da3e058bc7cdf6ac`

## OPT-A authority

- Seal ID: `OPT-A.GBPUSD.2025.v1`
- Seal hash: `85c1ce9f7721b33c4aef97a86561bd3c6fd8bc7681214a689d56bf147d4575d4`
- Complete 15M bars: `23,824`
- Quarantined touched/incomplete 15M buckets: `1,076`
- M1-derived 2H context bars: `2,633`
- 15M is the sole holdout hypothesis clock; 2H is context only.

## Frozen validation result

- Ratified hypotheses: `202`
- Evaluable: `202`
- Structurally reappeared: `197`
- Structurally not reappeared: `5`
- Counter-story alerts: `202`
- Deterministic reproduction: `PASS`
- Independent verification: `PASS`
- Validation manifest: `0411c0c45f5edcb1c83927ddc38be29064114778bd4a430f49fcd15221bcba75`
- Implementation tests: `102/102 PASS`

## Authority boundary

The release establishes data lineage, exact frozen structural recurrence and
the presence of competing responses. It establishes no independence,
probability, predictive edge, recommendation, trade, production, risk or
execution authority.

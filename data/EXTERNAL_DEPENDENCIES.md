# External data dependencies

No market dataset is committed to Git. Reproduction requires materializing the
following immutable OPT-A releases from external storage and verifying their
manifest hashes before use.

## Discovery authority — 2026 H1

- Seal: `OPT-A.GBPUSD.2026H1.v1`
- Seal hash: `0927f7a2b078d670370eb9ec26718f3e2ff0d97708df1f785a9333264415ef99`
- Scope: GBP/USD BID, UTC, `[2026-01-01, 2026-07-01)`
- Raw M1 SHA-256: `3d18d9a0a5d813522654543f49146f7841e2851c682aa946454cc685e26f67e0`
- Canonical 15M SHA-256: `6eca8ca9529968ae0a0594837886504bb4a2e5e17899857920089c1207b56c85`
- Canonical 2H SHA-256: `28acab32b3b5325709a3654dd909b3e7fe446fed0598a94b29a6cba10a29072c`
- Full dependency list: [`OPT_A_SEAL_MANIFEST.json`](../docs/history/releases/opt-a-discovery-2026-h1/OPT_A_SEAL_MANIFEST.json)

The manifest also binds the six provider H1 source files, reconciliation
tables, and reports by exact SHA-256.

## Validation authority — calendar year 2025

- Seal: `OPT-A.GBPUSD.2025.v1`
- Seal hash: `85c1ce9f7721b33c4aef97a86561bd3c6fd8bc7681214a689d56bf147d4575d4`
- Scope: GBP/USD BID, UTC, `[2025-01-01, 2026-01-01)`
- Raw M1 SHA-256: `613abc547b5a53ac982c02ae68c4c3046c69a737cb70a080da3e058bc7cdf6ac`
- Canonical 15M SHA-256: `27fa8a44006e43995cce5babbc4532786a4fb9aecda600def51106677eb86278`
- Context-only 2H SHA-256: `6c121e65dad293564009165589aabecfeb298dddc404b08efbff488b90dbf14d`
- Full dependency list: [`OPT_A_SEAL_MANIFEST.json`](../docs/history/releases/opt-a-validation-2025/OPT_A_SEAL_MANIFEST.json)
- Retrieval contract: [`DUKASCOPY_RETRIEVAL_MANIFEST.json`](../docs/history/releases/opt-a-validation-2025/retrieval/DUKASCOPY_RETRIEVAL_MANIFEST.json)

The 2025 release is consumed validation evidence and must not be presented as a
new untouched holdout.

## Resolution rules

- Materialized files must match the manifest byte hash before replay.
- A byte change creates a new release and seal; existing seals are immutable.
- Missing market records are never inferred or filled.
- External data paths are supplied to runner scripts at execution time.
- No external dataset grants trading or execution authority.

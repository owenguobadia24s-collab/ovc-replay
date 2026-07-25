# WP4 — Actual GBP/USD Provider Population Intake

## Result

**PASS — the complete governed provider population was acquired and audited.**

- Provider: Dukascopy
- Instrument: GBP/USD (`GBPUSD`)
- UTC interval: `[2021-01-01T00:00:00Z, 2026-01-01T00:00:00Z)`
- Calendar-month partitions: **60**
- Accepted source objects: **240**
- Accepted CSV rows across all four families: **3,781,810**
- Accepted CSV bytes: **216,656,289**
- Aggregate QA state: `PASS`
- Market authority: `NONE`
- R2 mutation: `NONE`

## Source-object families

Each month contains four independent provider objects:

- `M1_BID`
- `M1_ASK`
- `H1_BID`
- `H1_ASK`

## Research-role boundaries

| Role | Months | Source objects | Target release identity |
|---|---:|---:|---|
| Discovery | 2021-01 through 2023-12 | 144 | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` |
| Development | 2024-01 through 2024-12 | 48 | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` |
| Validation | 2025-01 through 2025-12 | 48 | `OPT-A.GBPUSD.VALIDATION.2025.v2` |

Validation remains `LOCKED_UNCONSUMED`. Intake grants no design, threshold, semantic, handoff or selector authority.

## Executed provider adapter

The successful execution used `OVC_DIRECT_BI5_CANDLE_ADAPTER` version `1.0.1` against Dukascopy's historical BI5 candle store.

The adapter:

- downloaded daily M1 BID and ASK BI5 objects;
- downloaded monthly H1 BID and ASK BI5 objects;
- retained exact compressed provider transport bytes;
- decompressed the provider records using the frozen candle field order;
- removed only zero-volume equal-OHLC flat records;
- wrote exact UTF-8 monthly CSV objects using:

```text
timestamp,open,high,low,close,volume
```

The earlier package-based adapter was superseded during pilot diagnosis and removed before final review.

## External execution plane

GitHub-hosted runners resolved `OVC_EXTERNAL_ARTIFACT_ROOT` under `RUNNER_TEMP`, outside the checked-out Git worktree. Every yearly job recorded capacity and created a non-overwriting workspace through the WP2 lifecycle API.

The successful workflow produced:

- five compressed yearly evidence artifacts containing source CSVs, exact BI5 transport objects and machine-readable records;
- sixty compact monthly summaries;
- one aggregate population summary and execution receipt;
- no release root, publication approval, selector or active handoff.

The five compressed yearly evidence artifacts total **85,076,759 bytes** and expire in August 2026 under the 30-day GitHub Actions retention policy. Compact summaries expire in October 2026 under the 90-day policy. Exact artifact IDs, sizes, digests and expiry times are recorded in `WP4_ACTIONS_ARTIFACT_INVENTORY.json`.

These Actions artifacts are temporary intake evidence. They are not the canonical R2 release store.

## QA conditions applied

Every accepted source object passed:

- exact month, role and release-identity binding;
- strictly increasing UTC timestamps;
- M1 or H1 boundary alignment;
- half-open monthly interval containment;
- exact ordered columns and schema fingerprint;
- finite positive OHLC values with valid ordering;
- non-negative provider-declared volume;
- SHA-256 and byte-count recording over accepted CSV bytes;
- `qa_state=PASS` and `availability_state=LOCAL_ONLY`;
- denial of release, selector, discovery-seed and market authority.

A missing, empty, malformed, duplicated, non-monotonic, misaligned or out-of-range object would have failed its yearly job and prevented aggregate completion.

## Execution evidence

- Workflow run: `30175183492`
- Successfully tested provider-code head: `242dd45fd482699f940fa1c237fc1b6e10650e77`
- Provider pilot: PASS
- 2021 yearly job: PASS
- 2022 yearly job: PASS
- 2023 yearly job: PASS
- 2024 yearly job: PASS
- 2025 yearly job: PASS
- Exact aggregate: PASS
- Aggregate summary: `WP4_POPULATION_INTAKE_SUMMARY.json`
- Execution receipt: `WP4_EXECUTION_RECEIPT.json`

## Authority boundary

WP4 performed actual provider intake. It did not:

- freeze mutable workspaces into role releases;
- publish any object to Cloudflare R2;
- activate an OPT-A selector;
- unlock or consume validation;
- activate the OPT-A-to-OPT-B handoff;
- authorise OPT-B/C/D conclusions, probability, exposure, trading or execution.

## Completion consequence

WP4 is complete once the sealed repository records pass final branch-head CI. The next bounded packet may construct and QA the role-aware OPT-A workspaces and releases, but release freezing, R2 publication and selector activation remain separate gated actions.
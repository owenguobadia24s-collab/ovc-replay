# WP4 — Actual GBP/USD Provider Population Intake

## Scope

WP4 acquires the governed Dukascopy GBP/USD population for the exact UTC interval `[2021-01-01T00:00:00Z, 2026-01-01T00:00:00Z)`.

The intake contains 60 calendar-month partitions and four source-object families per month:

- `M1_BID`
- `M1_ASK`
- `H1_BID`
- `H1_ASK`

Total planned source objects: **240**.

## Research-role boundaries

| Role | Months | Source objects | Target release identity |
|---|---:|---:|---|
| Discovery | 2021-01 through 2023-12 | 144 | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` |
| Development | 2024-01 through 2024-12 | 48 | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` |
| Validation | 2025-01 through 2025-12 | 48 | `OPT-A.GBPUSD.VALIDATION.2025.v2` |

Validation remains `LOCKED_UNCONSUMED`. Intake does not grant design, threshold, semantic or selector authority.

## Provider adapter

The workflow uses the pinned `dukascopy-node@1.46.4` adapter to access Dukascopy historical data and request independent BID and ASK OHLCV exports for M1 and H1. The adapter output is written as exact UTF-8 CSV bytes with the frozen ordered schema:

```text
timestamp,open,high,low,close,volume
```

The workflow also retains the adapter transport cache inside the external artifact bundle for each year. Raw and parsed market bytes never enter Git.

## External execution plane

GitHub-hosted runners create `OVC_EXTERNAL_ARTIFACT_ROOT` under `RUNNER_TEMP`, outside the checked-out Git worktree. Each yearly job records available capacity, creates a non-overwriting workspace through the WP2 lifecycle API, downloads twelve monthly partitions and emits:

- one compressed yearly evidence artifact containing source CSVs, transport cache and records;
- twelve compact monthly summaries;
- intake records and source-object identity records;
- no release root, publication approval, selector or handoff.

Yearly market-data artifacts are retained for 30 days. Compact summaries are retained for 90 days and the aggregate summary is committed to Git after all 60 months pass.

## QA conditions

Every accepted source object must have:

- exact month and role binding;
- strictly increasing UTC timestamps;
- M1 or H1 boundary alignment;
- timestamps inside the half-open monthly partition;
- exact ordered columns and schema fingerprint;
- finite positive OHLC values with valid ordering;
- non-negative provider-declared volume;
- SHA-256 and byte count over the accepted CSV object;
- `qa_state=PASS` and `availability_state=LOCAL_ONLY`;
- no release, selector, discovery-seed or market authority.

A missing, empty, malformed, duplicated, non-monotonic, misaligned or out-of-range object fails its yearly job and prevents aggregate completion.

## Authority boundary

WP4 performs actual provider intake. It does not:

- freeze the mutable workspaces into role releases;
- publish any object to Cloudflare R2;
- activate any OPT-A selector;
- unlock or consume validation;
- activate the OPT-A-to-OPT-B handoff;
- authorise OPT-B/C/D conclusions, probability, exposure, trading or execution.

## Completion rule

WP4 passes only when the pilot succeeds, all five yearly jobs succeed, exactly 60 monthly summaries aggregate, exactly 240 source-object identities are accepted and final repository CI remains green after the compact execution records are committed.
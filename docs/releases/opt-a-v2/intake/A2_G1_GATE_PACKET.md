# A2-G1 — Population Intake Integrity

## Result

**PASS.** The complete WP4 GBP/USD provider population has byte identity and request lineage sufficient to enter governed mutable role workspaces.

## Evidence inspected

The five WP4 yearly evidence artifacts were downloaded and expanded independently of the Git worktree. The audit covered:

- 60 UTC calendar-month partitions;
- 240 accepted M1/H1 BID/ASK source objects;
- 3,781,810 accepted CSV rows;
- 216,656,289 accepted CSV bytes;
- 3,772 retained Dukascopy BI5 transport chunks;
- all intake records, source identities, downloader receipts and monthly summaries.

## Integrity checks

Every accepted source object was required to prove:

- SHA-256 and byte count agreement across the CSV, downloader receipt, intake record and source identity;
- provider request lineage including interval, instrument, timeframe, side and deterministic parameter hash;
- retained transport-object SHA-256, byte count, provider URL and provider metadata;
- QA state `PASS`, explicit research role and source-object identity;
- explicit duplicate, timestamp, schema, gap and quarantine disposition metadata.

Observed violations: **0**.

No missing transport partition was silently omitted. No quarantine record was required by the accepted population.

## Authority change

A2-G1 authorises the verified provider objects to enter the governed mutable discovery, development and locked-validation workspaces.

It does not authorise:

- observation construction or acceptance as candidate OPT-A outputs;
- release freezing;
- Cloudflare R2 publication;
- selector activation;
- validation consumption;
- OPT-A-to-OPT-B handoff;
- market, probability, exposure, trading or execution authority.

## Next gate

`A2-G2 — Observation construction` / `WP5 — role workspace construction and QA`.

# OPT-A Provider Intake and Source-Object Contract v0.2

## Authority boundary

This contract freezes the provider-facing identity and intake-record rules for the OPT-A v2 GBP/USD population programme. It is a design and test authority only. WP3 performs no provider request, downloads no market bytes, creates no role release, writes nothing to R2 and activates no selector.

Programme: `OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2`  
Contract ID: `OPT-A-PROVIDER-INTAKE-SOURCE-OBJECT-0.2`

## Provider and population identity

- Provider: `DUKASCOPY`
- Instrument: `GBPUSD`
- Population interval: `[2021-01-01T00:00:00Z, 2026-01-01T00:00:00Z)`
- Native source timeframes: `M1`, `H1`
- Price sides: `BID`, `ASK`
- Canonical timezone: `UTC`
- Required monthly source-object families:
  - `M1_BID`
  - `M1_ASK`
  - `H1_BID`
  - `H1_ASK`

The provider population is partitioned by UTC calendar month. A source object may not cross a month boundary or a research-role boundary.

## Exact role split

| Role | Release ID | Interval |
|---|---|---|
| Discovery | `OPT-A.GBPUSD.DISCOVERY.2021_2023.v2` | `[2021-01-01T00:00:00Z, 2024-01-01T00:00:00Z)` |
| Development | `OPT-A.GBPUSD.DEVELOPMENT.2024.v2` | `[2024-01-01T00:00:00Z, 2025-01-01T00:00:00Z)` |
| Validation | `OPT-A.GBPUSD.VALIDATION.2025.v2` | `[2025-01-01T00:00:00Z, 2026-01-01T00:00:00Z)` |

No source object may be shared between roles. Validation remains `LOCKED_UNCONSUMED` and cannot be used for model design, semantic naming, threshold selection or case selection.

## Source-object identity

Every downloaded provider object must receive one immutable identity with this logical form:

```text
SRC.DUKASCOPY.GBPUSD.<TIMEFRAME>.<SIDE>.<YYYY-MM>.v1
```

The identity binds:

- provider and provider instrument;
- native timeframe and price side;
- UTC half-open monthly interval;
- research role and target release ID;
- exact request parameters;
- exact response bytes, SHA-256 and byte count;
- parsed row count, first timestamp and last timestamp;
- ordered source schema and schema fingerprint;
- downloader/build implementation version;
- immutable local object path relative to the external workspace.

A byte change, request-parameter change, schema change or provider correction creates a new source-object version. Existing identities are never overwritten.

## Provider-intake record

Each request attempt produces a machine-readable record, including failed and quarantined attempts. An accepted intake record requires:

- a unique `intake_id` and exact `source_object_id`;
- request interval equal to the source object's monthly interval;
- provider response status and content type;
- byte count and lowercase SHA-256 of the complete response;
- parser schema fingerprint;
- row count and timestamp bounds when parsing succeeds;
- explicit `qa_state`, `availability_state` and disposition;
- no secrets, cookies, tokens, local absolute paths or credential material.

Allowed attempt dispositions are:

- `ACCEPTED_WORKSPACE_INPUT`
- `RETRYABLE_PROVIDER_FAILURE`
- `QUARANTINED_HTTP_RESPONSE`
- `QUARANTINED_SCHEMA_MISMATCH`
- `QUARANTINED_CONTENT_MISMATCH`
- `QUARANTINED_TIME_RANGE_MISMATCH`
- `BLOCKED_CONFIGURATION`

Only `ACCEPTED_WORKSPACE_INPUT` may enter the mutable OPT-A workspace. It still has no release or market authority.

## Schema fingerprint

The schema fingerprint is SHA-256 over canonical UTF-8 JSON containing, in order:

1. source column names;
2. logical data types;
3. timestamp unit and timezone semantics;
4. decimal parsing and precision rules;
5. volume field name and declared unit or `UNKNOWN`;
6. missing-value representation;
7. parser contract version.

Column order is authoritative. A changed order, type, timestamp convention, side convention or volume declaration is a schema change and requires quarantine or a new reviewed schema version.

## Data-boundary rules

- BID and ASK are separate provider objects and separate observation chains.
- A source object never mixes timeframes, sides, instruments, providers or roles.
- Midpoint authority is `NONE`.
- Missing provider rows are never filled, interpolated, forward-filled, reverse-filled or inferred from H1.
- H1 provider-native objects are independent corroboration inputs; they may not manufacture M1 detail.
- Duplicate timestamps are not silently deduplicated. Identical duplicates are quarantined as `DUPLICATE_IDENTICAL`; conflicting duplicates are quarantined as `DUPLICATE_CONFLICT`.
- Unparseable, non-UTC, out-of-partition or out-of-order records are quarantined with explicit reason codes.
- Raw response bytes and parsed market rows remain outside Git under `OVC_EXTERNAL_ARTIFACT_ROOT`.

## Required QA reason codes

```text
PROVIDER_RESPONSE_MISSING
PROVIDER_RESPONSE_NON_SUCCESS
CONTENT_TYPE_UNEXPECTED
CONTENT_HASH_MISMATCH
SCHEMA_FINGERPRINT_MISMATCH
TIMESTAMP_PARSE_FAILURE
TIMESTAMP_NOT_UTC
TIMESTAMP_OUTSIDE_PARTITION
TIMESTAMP_OUT_OF_ORDER
DUPLICATE_IDENTICAL
DUPLICATE_CONFLICT
SIDE_MISMATCH
TIMEFRAME_MISMATCH
INSTRUMENT_MISMATCH
EMPTY_OBJECT
```

## WP3 consequence

The schemas and fixtures governed by this contract may be used to implement and test later intake code. They cannot be treated as provider evidence, discovery observations, release parents or selector inputs. Actual population execution remains blocked until `A2-G0` passes.
# OPT-A Clock, Aggregation, Gap, Volume and Reconciliation Contract v0.2

## Authority boundary

This contract freezes the deterministic observation rules that a later OPT-A v2 implementation must follow. It defines no market conclusion and creates no active release.

Contract ID: `OPT-A-CLOCK-AGGREGATION-RECONCILIATION-0.2`

## Time semantics

- All timestamps are UTC.
- Every interval is half-open: `[open, close)`.
- Bar timestamps identify interval open.
- Daylight-saving changes do not move or rename any boundary.
- Calendar-month source partitions also use half-open UTC intervals.
- A bucket is complete only when its exact expected timestamp set is present, not merely when its row count is correct.

## Source and derived observation identities

| Identity | Role |
|---|---|
| `M1_PROVIDER_NATIVE` | Detailed provider source object |
| `H1_PROVIDER_NATIVE` | Independent provider corroboration object |
| `H1_M1_DERIVED` | Exact aggregation of 60 native M1 rows |
| `M15_M1_DERIVED` | Exact aggregation of 15 native M1 rows |
| `H2_M1_CHAIN_DERIVED` | Two consecutive `H1_M1_DERIVED` bars, equivalent to 120 exact M1 rows |
| `H4_M1_CHAIN_DERIVED` | Optional two consecutive accepted H2 bars |
| `D1_M1_CHAIN_DERIVED` | Optional twelve consecutive accepted H2 bars |

`H1_PROVIDER_NATIVE` and `H1_M1_DERIVED` are permanently distinct identities. Provider-native H1 may corroborate, disagree with or be absent from the M1-derived chain; it may never replace missing M1 rows or become hidden lineage for a derived 15M, H1, 2H, 4H or D1 bar.

## A-L operating spine

The primary operational spine is the fixed UTC 2H partition:

| Label | UTC interval |
|---|---|
| A | `[00:00, 02:00)` |
| B | `[02:00, 04:00)` |
| C | `[04:00, 06:00)` |
| D | `[06:00, 08:00)` |
| E | `[08:00, 10:00)` |
| F | `[10:00, 12:00)` |
| G | `[12:00, 14:00)` |
| H | `[14:00, 16:00)` |
| I | `[16:00, 18:00)` |
| J | `[18:00, 20:00)` |
| K | `[20:00, 22:00)` |
| L | `[22:00, 00:00 next day)` |

Labels are clock identities only. They do not encode session names, semantic states or trading claims.

## Exact bucket requirements

| Output | Required parent timestamps per side | Acceptance rule |
|---|---:|---|
| 15M | 15 M1 | exact consecutive minute opens |
| H1 M1-derived | 60 M1 | exact consecutive minute opens |
| 2H A-L | 2 accepted H1 M1-derived / 120 M1 | exact pair at an A-L boundary |
| 4H optional | 2 accepted 2H bars / 240 M1 | exact consecutive pair on a 4H UTC boundary |
| D1 optional | 12 accepted 2H bars / 1,440 M1 | exact UTC day partition |

An incomplete, duplicated, out-of-order or side-misaligned parent set is quarantined. The implementation must not emit a partial canonical bucket.

## Deterministic OHLC aggregation

For each side independently:

- open: first parent open;
- high: maximum parent high;
- low: minimum parent low;
- close: final parent close;
- parent count: exact expected count;
- lineage: ordered parent identity list or deterministic lineage digest;
- arithmetic: decimal, never binary floating-point authority.

Prices are compared as canonical decimal values. Trailing-zero formatting differences do not change value identity. No unratified tolerance band may convert a mismatch into a match.

## BID/ASK pairing

A paired observation requires BID and ASK buckets with identical instrument, timeframe identity, interval and exact parent timestamp set. Pair quality states are:

```text
PAIRED_VALID
MISSING_BID
MISSING_ASK
TIMESTAMP_SET_MISMATCH
NEGATIVE_SPREAD
SIDE_LINEAGE_MISMATCH
QUARANTINED_PARENT
```

ASK must be greater than or equal to BID for every comparable open, high, low and close field. Midpoint bars are not authorised.

## Gap and quarantine policy

No-fill is absolute. The following methods are prohibited:

- interpolation;
- forward fill or reverse fill;
- synthetic flat candles;
- lower-resolution inference;
- provider-native H1 substitution for missing M1;
- cross-side substitution;
- silent duplicate removal;
- silent timezone repair.

Gap records bind the source object, side, expected timestamp, surrounding observed timestamps, reason code and affected bucket identities. Quarantined rows remain traceable and cannot enter accepted aggregation parents.

Required gap/quality reason codes include:

```text
EXPECTED_TIMESTAMP_MISSING
UNEXPECTED_TIMESTAMP_PRESENT
INCOMPLETE_BUCKET
DUPLICATE_IDENTICAL
DUPLICATE_CONFLICT
NON_MONOTONIC_TIME
OUTSIDE_INTERVAL
SIDE_PAIR_MISSING
NEGATIVE_SPREAD
PARENT_QUARANTINED
```

## Volume policy

- Volume remains provider-declared data, not a universal market-volume claim.
- BID and ASK volume are retained separately.
- The intake record must declare the provider field, unit and interpretation, or `UNKNOWN`.
- Known additive volume may be summed only within one side and one exact accepted bucket.
- Unknown, missing, inconsistent or non-additive volume produces a quality state and nullable aggregate; it is never silently normalised to zero.
- H1 provider-native volume and M1-derived H1 volume are compared only when the declared units and semantics are identical.

Volume quality states:

```text
KNOWN_ADDITIVE
KNOWN_NON_ADDITIVE
UNKNOWN_UNIT
MISSING
INCONSISTENT_UNIT
NOT_COMPARABLE
```

## H1 reconciliation

Reconciliation aligns `H1_M1_DERIVED` and `H1_PROVIDER_NATIVE` by instrument, side and exact UTC interval. It is a QA comparison, not a substitution rule.

Price comparison uses canonical decimal equality for open, high, low and close. Volume is evaluated separately. Required results are:

```text
MATCH_EXACT
OHLC_MISMATCH
M1_DERIVED_MISSING
PROVIDER_NATIVE_MISSING
BOTH_QUARANTINED
VOLUME_MATCH
VOLUME_MISMATCH
VOLUME_NOT_COMPARABLE
```

Every mismatch record includes both bar identities, both lineage references, field-level values and reason codes. A release QA summary reports counts by role, month, side and result. Unresolved reconciliation may produce `WARN`, `BLOCK` or `QUARANTINE` according to a later ratified gate; it never silently edits either chain.

## Release-split invariants

- A derived bucket belongs to one and only one research role.
- A bucket crossing a role boundary is prohibited.
- Discovery, development and validation QA summaries are separate.
- Validation comparison outputs remain locked with the validation release and cannot inform discovery or development design without an explicit access approval.

## WP3 consequence

This contract authorises synthetic contract fixtures and deterministic validation tests only. Provider execution, release freezing, publication, selector activation and OPT-B consumption remain blocked.
# C1 v2 and exact OPT-A price-parent to C2 input profile v0.2

## Decision

C2 consumes two immutable parents as one verified input:

1. the exact active OPT-B.C1 v2 Discovery or Development release record; and
2. the exact OPT-A v2 price row identified by that record.

The C1 record remains the atomic-fact authority. The OPT-A row supplies only the absolute OHLC price parent that C1 deliberately does not duplicate. C2 must never add fields to, rewrite, relabel or rebuild the published C1 release.

## Exact join

Every joined input must satisfy all of these bindings:

- C1 release ID, manifest ID and manifest SHA-256 are exact and fully byte verified;
- OPT-A release ID, manifest ID and manifest SHA-256 are exact and fully byte verified;
- roles are identical and limited to Discovery or Development;
- instrument is `GBPUSD`;
- clock is `15M` or `2H_A_L`;
- price side is `BID` or `ASK`;
- the C1 `source_path` is declared by the OPT-A manifest and matches the clock and side;
- the C1 `timestamp_ms` resolves to exactly one row in that file;
- `source_bar_id` equals the deterministic identity of OPT-A release ID, source path and timestamp;
- current-bar price primitives and categorical direction reconcile exactly to the resolved OHLC row;
- C1 retains 17 numeric/null measurements plus categorical `direction`, representing the frozen 18-formula registry;
- open time is the OPT-A timestamp, and close/first-valid time is the exact clock end.

The immutable per-record state `CANDIDATE_LOCAL_ONLY` is accepted only inside an exact active, remote-verified C1 release envelope. Release authority is never inferred from a mutable field inside the published shard.

## Structural derivation

C2 derives levels and containers from chronological joined inputs using `C2.PARAMS.GBPUSD.DISCOVERY.v0.1`:

- range high, range low and midpoint require a complete clock-specific rolling window;
- swing high and swing low require the frozen left/right confirmation windows and become first-valid only after the right window closes;
- confirmed swing levels remain active until superseded or a source gap resets continuity;
- containers use only first-valid boundary levels;
- 15M-with-2H-parent uses the latest first-valid 2H structure not later than the 15M close;
- gaps reset history, persistence and transitions and are never bridged.

## Fail-closed rules

C2 rejects missing or mismatched manifests, undeclared paths, changed bytes, duplicate timestamps, missing price rows, mismatched bar IDs, primitive/price disagreement, cross-role joins, cross-side joins, future parent selection, Validation, legacy B-STATE parentage and downstream fields.

Manual shard concatenation, filename-only identity, OHLC reconstruction from C1 primitives, midpoint substitution, gap repair and reverse writes are prohibited.

## Authority

This reconciliation grants fixture trust for the actual two-parent shape and readies the exact-parent replay command. It grants no market replay result, C2 candidate release, publication, selector, activation, Validation consumption, probability, exposure, trading or execution authority.

# Portfolio Ledger and Projection Contract v0.1

## Packet and authority

- Programme: `OVC-PG-v0.2`
- Packet / gate: `PG-WP2` / `PG-G2`
- Authority: append-only programme-event capture and deterministic derived projection only

This contract grants no programme admission enforcement, migration, dependency-graph acceptance, Control Plane route, upkeep, market/model authority, selector or release mutation, Validation, publication, agent write, probability, risk, exposure, trading or execution authority.

## Append-only ledger

1. Ledger records are canonical UTF-8 JSON Lines with one newline-terminated event per line.
2. `event_id` is unique for the lifetime of a ledger.
3. Existing bytes are never edited, reordered or deleted by the service.
4. The write API exposes append only. Correction is a new event with `supersedes` lineage.
5. Every event is validated against the frozen event registry and source requirements before append.
6. An event with non-`NONE` authority effect requires an authoritative accepted operator-decision source.
7. Ledger inventory includes byte hash and per-event canonical hashes.

## Deterministic event order

Projection order is exactly:

1. `first_valid_at` ascending;
2. frozen event-type precedence ascending;
3. `event_id` ascending.

`observed_at`, local path, process time and file-system ordering never affect projection order.

## Projection boundary

- Projections are replaceable derived artifacts.
- A projection may show event-derived lifecycle, blocker and authority-event references.
- A projection cannot become an accepted decision or programme-owned state.
- Unknown event types, duplicate event IDs, orphan events and unregistered classes fail closed.
- Partitioning uses the frozen programme-class registry.
- Cross-partition checks require unique programme identity, no orphan events and no authority inheritance from graph or partition position.
- Same records and registries produce the same logical hashes.

## Source-state synchronisation

programme-owned machine-readable state is the effective state. The synchroniser compares but never writes the source:

- a source/projection commit mismatch emits `STALE_PROJECTION`;
- a material field mismatch emits `STATE_SOURCE_CONFLICT`;
- effective state remains the programme-owned record;
- `repair_performed` is always false;
- enforcement remains disabled before `PG-G6`.

## Failure handling

- malformed or duplicate event: `BLOCK`;
- missing authoritative source for authority effect: `QUARANTINE`;
- unknown programme/class/event: `BLOCK`;
- source state unavailable: `NOT_EVALUABLE`;
- source/projection conflict: `STATE_SOURCE_CONFLICT`, blocking for derived-current-state claims;
- stale input: `STALE_PROJECTION`, blocking for current portfolio claims.

## Storage boundary

Compact contracts, code, fixtures, tests, manifests and QA stay in Git. Large event streams and generated projections remain outside Git with checksum-addressed manifests. Test fixtures are compact and non-authoritative.

## Rollback

Discard and rebuild projections from the preserved append-only event ledger and accepted source records. Never rewrite the ledger or programme-owned state. Supersede defective code or contracts through new versions.

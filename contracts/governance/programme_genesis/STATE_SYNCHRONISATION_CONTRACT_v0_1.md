# OVC Programme State Synchronisation Contract v0.1

## Purpose

Preserve programme-owned machine-readable state as the authoritative current-state source while allowing Programme Genesis (`OVC-PG-v0.2`) to build deterministic, freshness-checked portfolio projections.

## Authority boundary

This contract grants read, validate, compare and derive authority only. It grants no authority to overwrite programme-owned state, accepted decisions, selectors, releases, plans, gate packets or historical records.

## Source precedence

For each programme, the accepted programme-owned state file and accepted decision records remain authoritative. The portfolio projection records:

- exact source path;
- source commit;
- source blob/content identity when available;
- plan and schema version;
- accepted decision links;
- projection build commit and logical hash.

## Synchronisation rules

1. PG consumes approved programme-state paths read-only.
2. A source update must be reflected in the next portfolio rebuild.
3. A projection may not infer PASS, authority or completion from code presence, tests, PR titles or merge history when accepted programme state is absent.
4. A lower-precedence source may fill only explicitly non-authoritative descriptive fields.
5. Missing fields remain `UNKNOWN`, `MISSING`, `NOT_EVALUABLE` or a registered migration state.
6. Conflicting accepted sources produce `STATE_SOURCE_CONFLICT`; the projector withholds a single current-state claim.
7. A stale projection produces `STALE_PROJECTION` and names the source and represented commits.
8. PG never repairs a programme-owned source file. Resolution requires a bounded correction in the owning programme or an append-only operator/delegated decision.
9. Partitioned builds must run cross-partition identity, dependency and authority consistency checks before portfolio PASS.
10. Disabling or deleting a derived local index loses no source authority.

## Required projection fields

- `programme_id`
- `source_state_path`
- `source_state_commit`
- `source_state_hash`
- `represented_status`
- `represented_packet`
- `represented_gate`
- `represented_authority`
- `source_freshness`
- `projection_commit`
- `projection_logical_hash`
- `health_findings`

## Health outcomes

- `SYNCHRONISED`
- `STALE_PROJECTION`
- `STATE_SOURCE_CONFLICT`
- `SOURCE_STATE_MISSING`
- `SOURCE_STATE_NOT_REPRODUCIBLE`
- `SCHEMA_UNSUPPORTED`
- `PARTITIONED_BUILD_WARNING`
- `PARTITIONED_BUILD_BLOCK`

## Enforcement

Before `PG-G6`, all enforcement consumers remain disabled. After adoption, a stale, conflicting, missing or non-reproducible source must fail closed for affected admission or merge-readiness decisions without blocking unrelated programme reads.

## Rollback

Disable PG projection/enforcement consumers and rebuild from accepted source states. Never rewrite source programme state through this contract.

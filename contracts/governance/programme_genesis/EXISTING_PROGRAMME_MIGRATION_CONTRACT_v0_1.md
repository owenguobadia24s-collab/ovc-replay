# Existing Programme Migration Contract v0.1

## Packet and authority

- Programme: `OVC-PG-v0.2`
- Packet / gate: `PG-WP4` / `PG-G4`
- Authority source: `PG-G3A.OPERATOR.ACKNOWLEDGE_CONTINUE.20260803T194700+0100`
- Authority: source-faithful provisional migration only

This contract authorises deterministic read-only import of programme-owned machine-readable state into provisional Programme Genesis migration records. It does not accept any imported programme fact or edge as canon. It grants no admission enforcement, Control Plane route, upkeep, market/model authority, semantic or threshold change, selector or release mutation, Validation, publication, agent write, probability, risk, exposure, trading or execution authority.

## Source boundary

1. Programme-owned machine-readable state is the authoritative source for current programme state.
2. Discovery is limited to registered repository roots and deterministic filename rules.
3. The native `OVC-PG-v0.2` state is excluded from legacy migration.
4. Every source is bound by repository-relative path and exact SHA-256 of source bytes.
5. Invalid JSON, absent `programme_id`, escaped paths and missing required registered sources fail closed.
6. Migration reads source records but never writes, repairs, normalises or reorders their accepted contents.

## Source-faithful field handling

- Source values are copied exactly into `preserved_values`.
- Alias selection is explicit in `source_field_map`; it does not reinterpret values.
- `programme_status` and `status` remain exact source strings.
- Authority objects remain exact source objects.
- Missing descriptive fields stay in `missing_descriptive_fields`.
- Missing native Genesis fields stay in `unresolved_fields`.
- `inferred_fields` is empty by default and may not be populated without a separately accepted source rule.
- Multiple source records for one programme are not silently combined.

## Permanent migration uncertainty

Every non-native import carries:

- `import_status: PROVISIONAL_NON_CANONICAL`;
- `authority_effect: NONE`;
- confidence based only on source coverage;
- exact source coverage;
- `inferred_fields`;
- `unresolved_fields`;
- `conflicting_fields`;
- a native-governance deadline;
- the visible `MIGRATION_UNCERTAINTY` banner.

The banner may be removed only after an accepted native Genesis record at a later authority-changing gate. Completion, recent modification, passing tests, a merged PR or graph position cannot remove it.

## Conflict ledger

The migration service produces a deterministic conflict ledger:

- materially different current-state values from multiple sources for one programme are `MIGRATION_SOURCE_CONFLICT` and `BLOCK`;
- missing native Genesis fields are `MIGRATION_UNRESOLVED_FIELDS` and `WARN`;
- missing descriptive fields are `MIGRATION_SOURCE_COVERAGE_GAP` and `WARN`;
- every finding has `authority_effect: NONE`;
- conflicts remain visible and are never resolved by source precedence inside the migration service.

A blocking conflict prevents a `PASS` migration snapshot but does not change the source programme.

## Active and terminal programmes

- Active or in-flight programmes receive deadline `BEFORE_NEXT_AUTHORITY_CHANGING_GATE_OR_PROGRAMME_BOUNDARY`.
- Completed, superseded, historical, retired or quarantined programmes receive deadline `BEFORE_REACTIVATION_OR_SUPERSESSION`.
- The deadline is a governance requirement, not an authority grant or automatic action.

## Determinism and storage

The same repository source bytes and migration registry produce the same:

- source paths and hashes;
- migration identities;
- field coverage;
- uncertainty findings;
- conflict ledger ordering;
- logical snapshot SHA-256.

The compact registry, contract, schemas, tests, manifest and QA remain in Git. The generated portfolio migration snapshot is a replaceable derived artifact and may be generated in CI or locally. It must never contain raw market data, credentials or external payloads.

## Adoption boundary

`PG-G4=PASS` accepts only the migration mechanism, reproducible source census and provisional outputs. Canonical migration adoption, admission enforcement and the read-only Control Plane route remain denied until the independent `PG-G6` operator decisions. Automatic upkeep remains denied until `PG-G7`.

## Rollback

Discard generated migration records and conflict ledgers, then rebuild from preserved programme-owned state and the frozen registry. Supersede defective contracts or code through a later version. Never rewrite source programme state, accepted decisions, source hashes or historical uncertainty findings.

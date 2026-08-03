# Portfolio Read Model and Disabled Control Plane Adapter Contract v0.1

## Packet and authority

- Programme: `OVC-PG-v0.2`
- Packet / gate: `PG-WP5` / `PG-G5`
- Baseline: lawful main after `PG-G4=PASS`
- Authority: deterministic read-only derivation, health evaluation, compact reporting and a disabled adapter candidate only

This contract grants no canonical portfolio adoption, migration adoption, admission enforcement, Control Plane route registration, automatic upkeep, market/model authority, semantic or threshold change, selector or release mutation, Validation, publication, agent write, probability, risk, exposure, trading or execution authority.

## Source contract

The read model consumes only:

1. a passing `ovc-programme-migration-snapshot/v1` whose `authority_effect` is `NONE`;
2. the native programme-owned `OVC-PG-v0.2` machine-readable state;
3. accepted compact graph evidence where supplied;
4. an exact lowercase 40-character repository source commit;
5. the frozen disabled Control Plane adapter registry.

Programme-owned machine-readable state remains authoritative. The read model is a replaceable derived view and may never repair, normalise, rewrite or outrank a source.

## Deterministic read model

- Programme rows are sorted by stable `programme_id`.
- Migrated rows preserve exact state, source path, source SHA-256, confidence, uncertainty, unresolved fields, conflicting fields and native-governance deadline.
- The native Programme Genesis row remains separate and is never passed through the migration adapter.
- All programme rows have `authority_effect: NONE`.
- Migrated rows have `canonical: false`; the native PG row alone has `canonical: true` for its own programme state, not for portfolio adoption.
- Status counts and health summaries are derived without interpretation.
- The same source commit, snapshot, native state and graph summary produce the same logical read-model SHA-256.
- A blocking migration snapshot, non-neutral authority effect or invalid source commit fails closed.

## Health contract

Health evaluation is read-only and source-linked:

- every migrated source path must still exist;
- every migrated source SHA-256 is recomputed from current repository bytes;
- missing sources or hash mismatches are `BLOCK`;
- missing migration uncertainty is `BLOCK`;
- unresolved native fields are retained as `WARN`;
- premature adapter activation is `QUARANTINE`;
- an activation gate other than `PG-G6` is `BLOCK`;
- health findings have `authority_effect: NONE`;
- health never writes, repairs, suppresses or resolves a source condition.

`PASS_WITH_WARNINGS` is a visible status, not a conversion of uncertainty into acceptance.

## Compact report contract

The compact report exposes only deterministic counts and statuses:

- programme and migrated-programme counts;
- migration and health warning counts;
- health blocking count;
- exact source commit;
- status distribution;
- disabled adapter status;
- retained PG-G6 and PG-G7 authority denials.

The compact report cannot grant authority, register a route or conceal underlying findings. Detailed records and findings remain available in the full read model and health report.

## Disabled Control Plane adapter

The candidate adapter is frozen with:

- `enabled: false`;
- `route_registered: false`;
- `read_only: true`;
- `write_enabled: false`;
- `enforcement_enabled: false`;
- `network_listener: false`;
- empty mutation methods;
- activation gate `PG-G6` and independent decision part `READ_ONLY_ROUTE`.

A locally constructed adapter payload is evidence of computability only. Local payload availability is not route authority. The adapter may not listen, serve, register, mutate, enforce, create programmes, approve gates, merge PRs or write `main`.

Any attempt to set enabled, route registration, write or enforcement true before `PG-G6` fails closed. A `PG-G5=PASS` accepts only the disabled adapter candidate and local deterministic projection.

## CLI boundary

The CLI may:

- build a provisional migration snapshot from registered source states;
- build the deterministic read model;
- evaluate health;
- emit the compact report;
- emit the disabled adapter projection;
- write only to an explicit output directory supplied by the caller.

The CLI may not modify repository source records, adapter registry values, authority decisions, branches, PRs, network routes or external systems.

## Adoption boundary

`PG-G5=PASS` releases only the consolidated `PG-G6` decision packet. `PG-G6` must decide four orthogonal authority deltas independently:

1. portfolio canon adoption;
2. provisional migration adoption;
3. admission enforcement activation;
4. read-only Control Plane route activation.

None is implied by the others. Automatic upkeep remains separately denied until `PG-G7`.

## Rollback

Discard and deterministically rebuild read models, health reports, compact reports and disabled adapter projections. Keep the adapter disabled and unregistered. Preserve programme-owned source state, migration records, warnings, decisions, hashes, graph evidence, PRs and commits. Supersede defective contracts or code non-destructively.

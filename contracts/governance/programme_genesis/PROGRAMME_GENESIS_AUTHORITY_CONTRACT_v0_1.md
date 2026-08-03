# Programme Genesis Authority Contract v0.1

## Status and authority

- Programme: `OVC-PG-v0.2`
- Packet: `PG-WP1`
- Gate: `PG-G1`
- Status: `FROZEN_CANDIDATE`
- Authority: bounded programme-governance records and validation only

This contract defines the first native Programme Genesis object boundary. It grants no programme admission enforcement, migration authority, Control Plane route, automatic upkeep, market/model authority, selector or release mutation, Validation access, publication, agent write, probability, risk, exposure, trading or execution authority.

## Constitutional invariants

1. Repository records are the court record; conversational direction is proposal context.
2. Accepted operator decisions outrank projections, implementation status and graph position.
3. Programme-owned machine-readable state remains authoritative for current programme state.
4. Unknown, inferred, stale, conflicting, orphaned and non-reproducible values are explicit values, not silent defaults.
5. Every authority field is fail-closed. Missing authority is `NONE`, never inherited.
6. A later object may reference or evaluate an earlier record but may not rewrite it.
7. Every accepted mutation is append-only or a versioned supersession with preserved lineage.
8. `PG-G3A` is mandatory before migration; `PG-G6` before enforcement/read-only route; `PG-G7` before upkeep.

## Canonical identities

All IDs are stable UTF-8 strings without local paths or timestamps unless the timestamp is part of the governed identity.

- `programme_id`: `OVC-<DOMAIN>-v<MAJOR.MINOR>` or an explicitly registered historical identifier.
- `genesis_id`: `GENESIS.<PROGRAMME_ID>.<REVISION>`.
- `plan_id`: stable plan identity independent of file name.
- `event_id`: `PGE.<PROGRAMME_ID>.<EVENT_TYPE>.<DETERMINISTIC_SUFFIX>`.
- `edge_id`: `PGEDGE.<FROM>.<TYPE>.<TO>.<REVISION>`.
- `authority_envelope_id`: `PGAUTH.<PROGRAMME_ID>.<REVISION>`.
- `scope_audit_id`: `PGSCOPE.<PROPOSAL_ID>.<REVISION>`.

## ProgrammeGenesis required fields

A native Genesis record requires:

- identity: `genesis_id`, `programme_id`, `programme_class`, title and version;
- governing sources: accepted plan, operator decision, baseline commit and source paths;
- purpose and scope: problem statement, included work, excluded work and termination condition;
- parentage: constitutional parent and any explicitly accepted programme parents;
- authority envelope: current authority, reserved denials and future operator gates;
- lifecycle: status, current packet, current gate, blockers and next action;
- admission evidence: one or more creation triggers plus a valid `SCOPE_AUDIT` against exactly three similar programmes;
- provenance: created time, actor, commit and supersession lineage;
- rollback: non-destructive rollback and retained evidence.

## Programme creation decision rule

A proposal is `ADMISSIBLE_FOR_GENESIS_REVIEW` only when:

1. at least one registered creation trigger is present;
2. all three nearest existing programmes are identified;
3. each comparison records why the proposed work cannot lawfully fit as a packet, correction, incident or bounded maintenance action;
4. no comparison is `UNKNOWN` or missing;
5. reserved authority remains denied unless an explicit operator gate is named.

A passing scope audit does not create or activate a programme. It only permits a Genesis proposal gate.

## Programme classes

Classes come only from `PROGRAMME_CLASS_REGISTRY_v0_1.json`. A class controls partitioning and validation, not authority. No class grants market, release, write, exposure or execution capability.

## Event boundary

Every material change is represented by a `ProgrammeEvent` with:

- immutable event identity and event type;
- exact programme and source record;
- observed time and first-valid time;
- actor class;
- prior and proposed lifecycle/authority values when applicable;
- evidence references and hashes where available;
- explicit authority effect (`NONE` unless an accepted decision grants it);
- supersession lineage and rollback.

Events cannot mutate accepted source records. Derived projections consume events in deterministic order: first-valid time, event precedence, then event ID.

## Edge boundary

Dependency edges are typed, directed and source-linked. Only `SOURCE_EXPLICIT` hard prerequisites may satisfy a hard gate before operator acceptance. `ADAPTER_INFERRED` edges remain provisional and cannot establish authority, completion or admissibility.

Reverse authority is prohibited: a downstream programme, implementation, test, QA result, PR or graph edge cannot grant authority to an upstream source or itself.

## Source precedence

1. accepted Genesis records and operator decisions;
2. accepted authority/gate/selector/publication/retirement decisions;
3. programme-owned state;
4. canonical manifests and evidence references;
5. ratified plans and registries;
6. merged PR and commit metadata;
7. open PRs/branches;
8. chat and uncommitted context.

Lower-precedence records may fill only explicitly descriptive fields. They may never replace a higher-precedence value or convert `UNKNOWN` into `PASS`.

## Validation outcomes

- `PASS`: contract and registry checks pass; no authority is implied.
- `WARN`: reproducible non-blocking limitation with named affected fields.
- `BLOCK`: required identity, source, scope audit, lineage or authority boundary is invalid.
- `QUARANTINE`: source conflict, reverse authority, hard cycle candidate, forged acceptance or non-reproducible authority evidence.
- `NOT_EVALUABLE`: required authoritative source is unavailable.

## Rollback

Disable and rebuild derived artefacts from accepted source records. Never delete or rewrite accepted Genesis records, events, decisions, PRs or evidence. Corrections are new append-only records that supersede the defective record while preserving its identity and reason.

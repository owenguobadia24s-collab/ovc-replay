# OVC Programme Genesis, Portfolio Ledger & Dependency Graph

## Implementation Plan v0.2 REVISED

- **Programme ID:** `OVC-PG-v0.2`
- **Document ID:** `OVC-PG-IMPLEMENTATION-PLAN-0.2`
- **Governance owner:** OVIS Control Plane / human operator
- **Status:** REVISED PROPOSED — operator ratification required at `PG-G0`
- **Baseline:** latest lawful `main` pinned by `PG-00`
- **External source identity:** ChatGPT File Library `file_00000000a0e4822f8ed73a5903ded4d7`
- **Supersedes:** `OVC-PG-IMPLEMENTATION-PLAN-0.1` design proposal

## Authority notice

This plan authorises repository design and bounded implementation work for programme-governance records, validators, migration tooling, deterministic read models and disabled Control Plane adapters only after `PG-G0=PASS` is recorded. It does **not** authorise market-data intake, formula or threshold change, model or semantic promotion, selector activation, publication, Validation access, agent write authority, probability, exposure, risk, trading or execution. Existing accepted programme decisions remain authoritative and may not be rewritten by migration.

## Primary decision

Build one additive programme-governance layer inside `ovc-replay`:

1. Every programme receives a source-linked Genesis record.
2. Every material change becomes an append-only Portfolio Event.
3. Deterministic projections produce current programme and portfolio state.
4. A typed dependency graph exposes prerequisites, governance, supersession, blockers and downstream impact.
5. Existing programmes are imported source-faithfully and remain visibly provisional where records are incomplete, inferred or conflicting.
6. New-programme admission enforcement and the read-only Control Plane route remain disabled until the final `PG-G6` operator decision.
7. Automatic upkeep remains disabled until the separate `PG-G7` operator decision.

## Constitutional principles

- Repository state is the court record; chat is proposal context.
- Programme-owned machine-readable state remains authoritative for that programme.
- Capability, QA, availability, programme status and authority are orthogonal dimensions.
- Code, tests, merged PRs and graph position never self-grant authority.
- Unknown, stale, conflicting, orphaned, inferred and non-reproducible conditions remain explicit.
- Derived portfolio views never outrank accepted source records.
- Migration may preserve or expose gaps; it may not silently repair accepted history.
- No file deletion, force-push, history rewrite, branch deletion or destructive migration is permitted.

## Programme Creation Test

A new programme is admitted only when at least one material trigger exists and the work cannot lawfully fit inside an existing packet, correction, incident or maintenance authority:

- new authority domain;
- multi-packet lifecycle;
- independent research or release line;
- cross-cutting shared service;
- programme supersession;
- portfolio-level operator decision.

Every proposal must include a `SCOPE_AUDIT` comparing the three most similar existing programmes and demonstrating negative fit. Ambiguity is resolved at a Genesis proposal gate, not by naming a branch.

## Required architectural corrections

1. **Graph acknowledgement before migration.** `PG-G3A` is an operator-required stop after dependency-graph validation and before `PG-WP4` migration.
2. **Permanent migration uncertainty.** Every imported non-native programme displays confidence, source coverage, `inferred_fields`, `unresolved_fields` and a native-governance deadline until a native Genesis record is accepted at a later authority-changing gate.
3. **Maintenance authority.** A versioned `MAINTENANCE_AUTHORITY_REGISTRY` defines bounded hygiene exemptions, path/title rules, size and authority ceilings, and escalation behaviour.
4. **State synchronisation.** The `STATE_SYNCHRONISATION_CONTRACT` preserves programme-owned state as authoritative; divergence produces `STALE_PROJECTION` or `STATE_SOURCE_CONFLICT`.
5. **Scope-gaming resistance.** New-programme proposals require negative-fit evidence against the three closest existing programmes.
6. **Scalable rebuilds.** Portfolio projection is partitioned by constitutional parent or programme class, with cross-partition identity, edge and authority checks.
7. **Bounded upkeep.** Post-adoption collectors may create append-only candidate events only on a dedicated branch after `PG-G7`; they cannot create programmes, approve, merge or write `main`.

## Canonical object model

- `CanonNode`
- `ProgrammeGenesis`
- `PlanVersion`
- `ProgrammeEvent`
- `ProgrammeStateProjection`
- `DependencyEdge`
- `AuthorityEnvelope`
- `PortfolioSnapshot`
- `MigrationRecord`
- `PortfolioHealthFinding`
- `MaintenanceAuthorityRecord`
- `ScopeAuditResult`
- `MigrationUncertaintyBanner`
- `UpkeepCandidateEvent`

## Source precedence

1. Accepted Genesis registrations and operator decisions.
2. Accepted gate, authority, selector, publication, retirement and supersession decisions.
3. Programme-owned machine-readable state.
4. Canonical manifests and immutable evidence references.
5. Ratified plans and contract registries.
6. Merged PR metadata and commit history.
7. Open PRs and branches as proposal/current-work evidence only.
8. Chat, screenshots and uncommitted files as non-authoritative context.

A lower-precedence source may fill an explicitly non-authoritative descriptive field but may never override an accepted decision or convert `UNKNOWN` into `PASS`.

## Work-packet and gate sequence

| Packet / gate | Branch | Primary output | Next boundary |
|---|---|---|---|
| `PG-00` | `gate/pg-g0-ratification` | Plan ratification packet, baseline manifest, maintenance registry, state synchronisation contract and initial programme state | `PG-G0` operator decision |
| `PG-WP1` | `build/pg-wp1-genesis-contract` | Genesis authority contract, schemas, class/edge/event registries, scope-audit schema and fixtures | `PG-G1` auto-ratifiable when wholly non-reserved |
| `PG-WP2` | `build/pg-wp2-portfolio-ledger` | Append-only event service, deterministic partitioned projection and source-state synchronisation | `PG-G2` auto-ratifiable when wholly non-reserved |
| `PG-WP3` | `build/pg-wp3-dependency-graph` | Typed graph, cycle/type/authority-path validators and impact analysis | `PG-G3`, then mandatory `PG-G3A` acknowledgement |
| `PG-WP4` | `migration/pg-wp4-existing-programmes` | Source-faithful imports, migration uncertainty and conflict ledger | `PG-G4` auto-ratifiable after `PG-G3A` |
| `PG-WP5` | `build/pg-wp5-read-model-control-plane` | CLI, health, compact reports, deterministic read model and disabled adapters | `PG-G5` auto-ratifiable when wholly non-reserved |
| `PG-G6` | `gate/pg-g6-portfolio-adoption` | Four orthogonal operator decisions: canon, migration, enforcement and read-only route | operator required |
| `PG-WP6 / PG-G7` | dedicated upkeep branch | Bounded candidate-event collector and upkeep activation packet | operator required |

## Continuous execution boundary

After `PG-G0=PASS`, execution may continue automatically through `PG-WP1`–`PG-WP3` and passing non-reserved gates. It must stop at `PG-G3A`. After `ACKNOWLEDGE_CONTINUE`, it may continue through `PG-WP4`–`PG-WP5` and passing non-reserved gates, then stop at `PG-G6`. `PG-G7` is separately operator-required.

## Migration policy

- Completed and historical programmes may retain explicit non-authority legacy gaps.
- Active programmes require stable identity, class, parents, plan, current state, authority, blockers and next action before their next authority-changing gate.
- In-flight programmes at `PG-G6` may receive one visible provisional waiver lasting only until the next gate or programme boundary.
- Imported edges distinguish `SOURCE_EXPLICIT` from `ADAPTER_INFERRED`; inferred edges cannot satisfy hard prerequisites without operator acceptance.
- Ordinary maintenance must match an active maintenance authority entry; unmatched or expanded work becomes `NOT_EVALUABLE` and is reviewed rather than fabricated into a programme.

## Gate authority

- `PG-G0`, `PG-G3A`, `PG-G6` and `PG-G7` are operator-required.
- `PG-G1`–`PG-G3` and `PG-G4`–`PG-G5` may auto-ratify only when every acceptance condition passes, QA recommends PASS, the delta is wholly non-reserved and rollback is defined.
- No automatic gate may grant selector, publication, Validation, semantic/model promotion, agent write, probability, exposure, risk or execution authority.

## Rollback

Rollback is non-destructive. Disable derived services, restore the prior selector or enforcement configuration where applicable, and preserve all source records, decisions, events, migration findings, PRs and commits. A derived projection may be deleted and rebuilt locally; accepted source authority may not be rewritten.

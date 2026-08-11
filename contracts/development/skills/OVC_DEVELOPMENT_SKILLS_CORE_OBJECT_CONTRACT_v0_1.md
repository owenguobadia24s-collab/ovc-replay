# OVC Development Skills Core Object Contract v0.1

Plan: `OVC-DSAI-IMPLEMENTATION-PLAN-0.2`  
Packet: `DSAI-WP1`  
Authority delta: `NONE`

## Governing sources

1. `OVC-DSA-DESIGN-SPEC-0.1-REVISED-1-RATIFIED` — Skill semantics, capability identity, maturity, availability, permission and non-authority rules.
2. `OVC-DSAI-IMPLEMENTATION-PLAN-0.2` — repository placement, WP1 acceptance, tests and rollback.
3. `contracts/development/OVC_SHARED_DEVELOPMENT_SERVICES_CONTRACT_v0_1.md` and existing `src/ovc/development/*` — reused for canonical identity, paths, QA/gate/rollback mechanics where semantically identical.

Repository sources remain authoritative over this projection. Missing authority is never inferred from this contract or any registry.

## Core object rules

- `CapabilityRecord` defines competence and prohibited interpretation; it never grants permission or authority.
- `SkillManifest` declares one immutable Skill release identity. WP1 freezes the schema only; immutable release closure/hashing is implemented in WP2.
- `SkillCapabilityBinding` maps a Skill release to a capability and conformance level.
- `SkillDependencyManifest` declares required/optional capability and Skill dependencies. Unknown mandatory dependencies fail closed.
- `SkillInputContract` and `SkillOutputContract` type invocation inputs and required/permitted/forbidden outputs.
- `ToolPermissionProfile` declares the maximum requested technical surface. Effective action still requires capability, reachability, permission, programme authority, packet scope and runtime policy.

## Vocabularies

Maturity: `EXPERIMENTAL`, `QUALIFIED`, `TRUSTED`.  
Availability: `UNAVAILABLE`, `AVAILABLE`, `SUPERSEDED`, `QUARANTINED`, `REVOKED`.  
Execution status: `PLANNED`, `RUNNING`, `PASS`, `BLOCKED`, `QUARANTINED`, `FAILED`, `NOT_EVALUABLE`.

`TRUSTED` is capability + release + environment scoped and affects resolver eligibility only. It never enlarges authority or permissions.

## Registry constitution

WP1 owns seed registries for Skill logical lineages, capabilities, permission profiles, tool bindings and execution profiles. Registry documents are projections, not authority records. Every registry carries `authority_effect: NONE` and `projection_only: true`.

Duplicate logical IDs are invalid. Unknown mandatory capability or dependency IDs are invalid. Superseded/revoked records remain addressable but are ineligible for new selection. Registry validation is deterministic and canonical JSON serialization reuses `ovc.development.identity`.

## Operator boundary projection

The operator-boundary registry is a source-referenced deny/projection surface only. It may classify a boundary as operator-reserved but cannot mark it approved, activated or satisfied. Activation, selector/family/semantic/scientific promotion, Validation, publication, exposure/execution, Skill TRUSTED promotion, Tool Broker activation, ORCH-1/2 and destructive/history-rewrite authority remain separately governed.

## Rollback

WP1 is one bounded additive change. Revert/supersede its contracts, schemas, registries and validator together. Do not rewrite historical DSAI evidence.
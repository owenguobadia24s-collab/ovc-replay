# OVC Development Skills Release, Knowledge and Environment Contract v0.1

Plan: `OVC-DSAI-IMPLEMENTATION-PLAN-0.2`  
Packet: `DSAI-WP2`  
Authority delta: `NONE`

## Release closure

A Skill release is an immutable normative bundle. Every source field is classified `NORMATIVE` or `DESCRIPTIVE` in the resolved release closure. Missing, unknown, mixed or ambiguous classification is treated as `NORMATIVE`; a descriptive exemption is never inferred. The release identity is `skill_id + semantic_version + canonical normative hash`. Explicitly descriptive-only changes therefore do not alter normative identity, while any normative change does.

Canonical serialization and SHA-256 reuse `ovc.development.identity`; WP2 does not fork identity mechanics.

## Knowledge Packs

A `KnowledgePackManifest` has dual identity: a source-set hash over exact source artifacts/fragments and a compiled-pack hash over the compiled logical pack. Compilation fails closed when a declared source or fragment is missing.

`KnowledgeDependencyGraph` edges bind exact source artifact identity + stable fragment selector + fragment hash to dependent capabilities/releases. When a stable mapped fragment changes, only the explicit dependants become stale. Deleted, ambiguous, remapped or otherwise unprovable selectors cause conservative whole-Pack invalidation.

Knowledge Pack staleness affects eligibility/qualification freshness only; it grants no authority and does not rewrite historical qualification evidence.

## Execution environment

`ExecutionEnvironmentManifest.reproducibility_class` is mandatory and explicit. It is never inferred from platform/tool strings. The environment identity binds OS, architecture, Python/runtime, toolchain, lockfile/base-environment identity and declared reproducibility class.

## Resolution/read models

Skill read models are deterministic projections from durable capability, Skill, release, Knowledge Pack and environment records. Resolution manifests/receipts are evidence of what was considered/resolved; they cannot make an unavailable/unqualified Skill eligible and cannot grant programme authority.

## Rollback

Remove/supersede WP2 release/knowledge/environment projections and schemas together. Existing shared identity utilities remain unchanged.
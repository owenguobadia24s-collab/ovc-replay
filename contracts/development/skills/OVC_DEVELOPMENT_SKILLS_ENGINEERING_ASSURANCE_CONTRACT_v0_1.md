# OVC Development Skills Engineering & Assurance Contract v0.1

Programme `OVC-DSAI-v0.1` — packet `DSAI-WP4 / DSAI-G4`.

This contract wraps existing `ovc.development` primitives; it does not fork their ownership. All first-generation engineering/assurance Skill candidates remain `EXPERIMENTAL`, operate in SHADOW/DRY_RUN or local-test planning mode, carry `authority_effect=NONE`, and have no default write or merge capability.

## Constructive Skills
`ovc-contract-builder`, `ovc-schema-builder`, `ovc-fixture-builder`, and `ovc-deterministic-implementation` emit deterministic artifact proposals only. Their output contract forbids authority decisions, selector/model promotion, merge execution, force-push and history rewrite.

`ovc-git-packet-manager` may plan bounded branch/commit/push/PR mechanics but cannot execute merge, force-push or history rewrite. Merge capability remains disabled/untrusted.

## BaseFreshnessPolicy
For mutating or merge-candidate packets, any main SHA movement requires re-preflight before the next write-side-effect barrier and before merge. Read-only work is fresh for no more than 5 main commits and strictly less than 30 elapsed minutes. Any dependency/write-set overlap forces immediate re-preflight. Packet policy may tighten but may not loosen those bounds.

## Assurance Skills
`ovc-test-planner` widens to dependent/repository assurance when impact is uncertain. `ovc-test-executor` emits a local test-execution plan only in this packet. `ovc-qa-evaluator`, `ovc-evidence-auditor`, and `ovc-gate-evaluator` separate technical acceptance from authority classification. Gate titles never determine authority.

## Reuse
Canonical hashing, head-churn classification, QA aggregation, gate records, preflight and other shared services remain owned by `src/ovc/development/`. WP4 imports/reuses them rather than copying their algorithms.

## Authority / rollback
No Skill is TRUSTED. Tool Broker and ORCH write/merge authority remain inactive. Rollback unregisters WP4 candidates; shared development primitives remain the fallback.

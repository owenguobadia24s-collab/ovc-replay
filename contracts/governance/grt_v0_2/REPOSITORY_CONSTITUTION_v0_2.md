# OVC GRT Repository Constitution v0.2

**Status:** `PROPOSED_UNADMITTED`  
**Activation:** `INACTIVE`  
**Design authority:** `OVC-GRT-V0.2-RCCC-DESIGN-SPEC-0.2-R1`  
**Authority effect:** `NONE_PRE_ENFORCEMENT`

## Constitutional purpose

This contract defines the pre-enforcement machine constitution that later GRT2 runtime packets must implement exactly. Physical repository observations are evidence; only versioned constitutional rules determine legality. Paths are locators, not sufficient governed-object identity.

## Core invariants

1. Repository artifacts have logical identity distinct from physical path.
2. Current and historical lifecycle classes are explicit and cannot be inferred from filenames such as `CURRENT`, `FINAL`, or `RATIFIED`.
3. Mandatory current relationships require source-explicit or lineage-explicit evidence.
4. Missing authority remains missing. GRT never infers deferred Programme Genesis adoption.
5. A scanner result is observation, not authority.
6. Severity, debt effect, and candidate-admission effect are independent fields.
7. The immutable historical baseline remains exactly 569 source records.
8. The eventual DebtFloor is monotonic: resolved debt can never regain grandfathering.
9. Optimization is subordinate to reference semantics.
10. GRT2-G2.5 and GRT2-G3 remain operator-required.

## Constituent bindings

The authoritative candidate identity is the canonical hash of the root, artifact-class, lifecycle, relationship, rule, current-state and information-architecture bindings plus `canonical-json-v1`. Supporting protocol hashes are retained as provenance but do not activate the Constitution.

## Decision algebra

The future reference runtime shall decide in this order: integrity failure → `INVALID`; operator-reserved semantic delta → `OPERATOR_REQUIRED`; new actionable findings, baseline expansion, unresolved lineage, or other mandatory failure → `FAIL`; otherwise → `PASS`. No weighted health score may offset one unlawful finding.

## Non-authority

Materializing this contract authorizes no blocking CI check, DebtFloor, owner reassignment, PGN adoption, cleanup, scientific authority, publication, probability, risk, exposure, execution, or agent write.

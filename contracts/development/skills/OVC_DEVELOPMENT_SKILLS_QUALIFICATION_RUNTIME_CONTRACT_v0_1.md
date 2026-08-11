# OVC Development Skills Qualification Runtime Contract v0.1

Programme `OVC-DSAI-v0.1` — packet `DSAI-WP6 / DSAI-G6`.

## Boundary
The Qualification Runtime determines whether an exact Skill release/capability/environment tuple has closed the evidence required by its registered `SkillEvaluationSuite`. It does not grant `TRUSTED`, activate Tool Broker writes, approve an operator-reserved gate, or mutate scientific/Validation/exposure authority.

## E1–E6 implementation binding
The runtime treats `E1` through `E6` as six mandatory registered evidence layers. Their labels in the suite registry are implementation bindings for evidence routing, not a redefinition of ratified design semantics. Every required layer must be present and PASS. Missing, stale, NOT_EVALUABLE, BLOCK/FAIL, mandatory-blocker or false-allow evidence blocks qualification. An aggregate score can never override a blocker.

## Qualification scope
A `SkillQualificationRecord` binds exact `skill_release_id`, `capability_id`, `environment_id`, Knowledge Pack hash, environment hash and evaluation-suite identity. Mechanical closure may advance an exact tuple only to `QUALIFIED`. A request for `TRUSTED` produces `GATE_REQUIRED`; the runtime never promotes it.

`CompositionQualificationRecord` is separate from individual qualification and requires all exact member qualifications plus explicit composition evidence.

## Requalification / incidents
Release, Knowledge Pack or environment drift makes the qualification stale. Operational observations and S1–S4 incidents are append-only evidence. S3 requires quarantine/containment; S4 additionally requires revocation. Incident state cannot silently restore maturity.

## Operator gate readiness and Review SLO
`OperatorGateReadinessRecord` carries `gate_ready_at`, `authority_kind`, exact candidate SHA, evidence closure, review target, queue age and consolidated-decision grouping. Missing a Review SLO has **zero authority effect**: it cannot auto-approve, promote, activate, preserve a stale candidate or waive evidence. Only candidates of the same authority kind may be consolidated, and each remains independently traceable.

## Parallel qualification
Parallel qualification is permitted only when fixture identities, execution environments and evidence stores are independent. Shared mutable evidence is a blocking conflict.

## Rollback
Disable Qualification Runtime admission and treat affected tuples as unqualified/stale. Preserve evaluation, incident and readiness evidence. No TRUSTED authority exists to revoke at G6.

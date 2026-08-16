# OVC Shared Systems v0.1 — Independent Pressure-Test Review

Review date: 2026-08-16
Reviewed plan: OVC-SHARED-SYSTEMS-CONFORMANCE-IMPLEMENTATION-PLAN-0.1 (PROPOSED)
Revised plan: OVC-SHARED-SYSTEMS-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-R1
Reviewed against main baseline: cd55c55cdf8e77d82940d0a1ce7191025f8b8514
Governing design: OVC-SHARED-SYSTEMS-DESIGN-SPEC-0.1-R1
Operator-gate doctrine: OVC_OPERATOR_RESERVED_GATE_DOCTRINE_v0_1

## Independent disposition

PASS WITH REVISION.

The proposed plan is structurally strong: it preserves one-owner/many-consumer governance, forbids domain-truth centralisation, separates semantic and physical execution identity, requires reference/optimised equivalence, reuses DSAI security rather than creating parallel authority stores, and stops before consumer cutover. The pressure-test found no reason to weaken the technical programme, but it found seven forward-conformance corrections required by current repository state and the ratified operator-gate doctrine.

## Accepted findings

1. **Stale owner premise.** The proposed plan treats the SharedServiceBinding as missing and makes owner selection part of SHSI-G0A. PR #954 has since materialised a GRT-conformant binding on main, naming OVC-SHARED-SYSTEMS-v0.1 as the single governance owner. Stage 0 must verify/source-bind this current record and prohibit duplicate owner materialisation.
2. **Gate-doctrine migration.** Gates must be classified by net-new authority delta. G0B-G10 are not operator stops merely because they are gates. Assurance-only gates are AUTO_RATIFIABLE; non-authoritative human/independent judgment is REVIEW_PREREQUISITE; only a net-new reserved delta is OPERATOR_REQUIRED.
3. **Too-narrow G0A envelope.** Authorising Stage 0 only would force another human boundary before deterministic inactive implementation. Ratification should grant one exact downstream AuthorityEnvelope covering WP0-WP10 inactive/reference implementation and already-lawful shadow comparison, while keeping activation/cutover and all other reserved deltas outside the envelope.
4. **PilotAcceptanceBudget discretion.** Numeric cap selection is not fully machine-determined by the proposed text. WP6 must record the derivation procedure and route any genuine judgment in cap selection to an independent operational REVIEW_PREREQUISITE rather than misclassifying it as operator authority.
5. **Real-corpus overconstraint.** Lack of a lawful real/governed-historical corpus must defer adoption-readiness for any affected optimised path, but must not by itself block the non-cutover SHARED_SYSTEMS_V0_1_IMPLEMENTED_THREE_CONSUMER_SHADOW_CONFORMANT terminal state if all shadow requirements pass.
6. **Owner-currentness race.** WP0 must pin the exact existing binding generation/hash and prove that no superseding or competing lawful binding exists at the candidate baseline.
7. **Current integration substrate.** Packet integration must use the repository-current lawful PIP/VIT/SIQ/final-integration route rather than hard-coding a legacy fresh-physical-main workflow. Any registered exception must be evidence-backed.

## Authority review

The revisions do not activate Shared Systems, change a consumer current path, promote any scientific/semantic object, add a source/provider/research role, expose Validation, publish canonical/R2 outputs, grant probability/risk/exposure/execution authority, alter the governance owner, waive a frozen invariant, or permit destructive action.

Recommended decision: PASS / RATIFY revised plan v0.2-R1.

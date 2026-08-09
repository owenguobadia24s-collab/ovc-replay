# C2 -> C2E Stable Comparison Signature Contract v0.3

Programme: `OVC-C2E-CAUSAL-EPISODE-CONFORMANCE-v0.2`  
Packet: `C2E2-G6-SIGNATURE-CONTRACT-REPAIR`  
Operator authority: `C2E2-G6-SIGNATURE-CONTRACT-SUPERSESSION.OPERATOR.SUPERSEDE.20260809T100800+0100`  
Authority: inactive, noncanonical candidate build/test only.

## Purpose

Repair the frozen v0.2 change-comparison defect without mutating historical C2AR identities or the historical v0.2 handoff. The v0.3 adapter carries two explicit deterministic comparison signatures: structural causal content for `PHASE_MUTATION` and selected-parent/dependency content for `RE_PARENT`.

## Additive versioning

`C2_TO_C2E_HANDOFF_CONTRACT_v0_2.md`, `c2e_input_frame/v0_2`, the original June empirical pack and all C2AR formula/link identities remain immutable historical evidence. The new adapter requires `contract_id=C2E.HANDOFF.SIGNATURE.v0_3` and `schema_id=c2e_input_frame/v0_3`.

## Structural comparison basis

The structural comparison basis contains exactly `LOCATION`, `MOTION`, `ORGANISATION`, and `INTERACTION`. Each axis contributes only its already-lawful first-valid computability status, reason codes, stable source-object identities and raw structural facts. It MUST NOT contain profile/output/record wrapper IDs, local observation identity, `as_of_time`, first-valid/evaluation chronology, selectors, fallback selections, outcomes, families, semantics, probability, risk, exposure or execution state.

A wrapper identity may remain in ordinary frame lineage and structural reference lists. It is excluded only from the v0.3 change-comparison digest. Equal lawful structural content therefore produces an equal structural comparison signature even when upstream wrapper IDs change because chronology advanced.

## Parent comparison basis

The parent basis contains only lawful selected parent observation IDs, selected parent structural-object IDs and explicit dependency states (`dependency_id`, role, status, reason codes). Local-observation-specific link IDs, context bundle IDs and chronology are lineage only and MUST NOT create `RE_PARENT` by themselves. Missing/not-computable dependency states remain explicit; they are never collapsed to neutral or unchanged.

## Boundary semantics

The six preregistered June baseline rule IDs and their stated meanings are unchanged. `PHASE_MUTATION` compares the stable structural signatures. `RE_PARENT` compares the stable parent signatures. Gap, release-end, continuation and birth semantics are unchanged. No threshold is introduced.

## Fail-closed rules

Unknown comparison fields fail closed. Any `record_id`, profile output ID, link/bundle ID, observation wrapper, as-of/FVT/cutoff field, family/outcome/semantic/probability/risk/exposure/execution input, selected/fallback object field or noncanonical numeric value in the comparison basis fails closed. Stored signatures are verified by deterministic reconstruction before boundary evaluation.

## Non-authority

This contract does not activate C2E or any boundary pack; grant a selector; authorize WP6; publish; consume Validation; promote semantic/family/candidate/theory state; or create probability, risk, exposure, execution or agent-write authority. WP6 remains denied until a fresh exact `C2E2-G6-RUN-AUTH` operator decision after replacement population/pack/envelope/manifest/token preparation.

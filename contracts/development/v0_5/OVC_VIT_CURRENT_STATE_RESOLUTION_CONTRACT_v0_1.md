# OVC VIT Current-State Resolution Contract v0.1

Status: corrective conformance contract under existing `DSAI3V-VIT-GENERAL-AUTHORITY-v0.1`  
Authority effect: `NONE_SAFETY_CONFORMANCE_CORRECTION`

## 1. Purpose

This contract prevents a historically true VIT gate or planning state from being presented as the current VIT state after a later lawful activation or rollback. It does not change VIT authority; it changes only how current state is resolved.

## 2. Canonical current-state route

Every query whose semantic request is `current VIT state`, `is VIT active`, `what authority does VIT currently have`, or an equivalent current-status question MUST resolve, in order:

1. `registries/implementation/dsai_vit_v0_3/CURRENT_STATE_POINTER.json`;
2. the exact programme-state record named by that pointer;
3. `registries/authority/DSAI3V_VIT_GENERAL_AUTHORITY_v0_1.json`;
4. `registries/authority/DEFAULT_EXECUTION_SUBSTRATE.json`.

The resolver MUST validate cross-record identity, programme, authority-reference and routing-scope consistency before returning a current status.

## 3. Historical evidence rule

VIT implementation plans, design documents, qualification packets, `GATE_READY` packets, pilot gate packets, general gate packets and release/closeout evidence remain immutable and queryable as history. They MUST NOT be selected as the controlling source for a current-status answer.

If the current pointer or current authority records are missing, malformed or mutually inconsistent, the result is `CURRENT_STATUS_UNRESOLVED`. The resolver MUST NOT fall back to an older plan or gate merely because that record is internally complete.

## 4. Non-transitivity

`QUALIFIED != AUTHORISED`; `AUTHORISED != ACTIVE`; `HISTORICALLY_DENIED != CURRENTLY_DENIED`; `HISTORICALLY_GATE_READY != CURRENTLY_GATE_READY`; `IN_GIT != CURRENT`.

Current status is established only by the current pointer/authority/substrate chain. Historical records establish what was true at their own generation.

## 5. Atlas and read-model consumption

System Atlas, Research Console Control projections, operator status summaries, automated preflight and any future read model that exposes current VIT `CURRENT`, `ACTIVE` or `AUTHORISED` predicates MUST consume `ovc.development.skills.vit_current_state.resolve_current_vit_query` or an implementation with an exact reference-equivalence receipt.

Atlas may show older gate states on the history plane, but they must be labelled historical and cannot override the current projection.

## 6. Failure policy

Resolution fails closed on missing current pointer, invalid pointer target, programme mismatch, authority mismatch, substrate/authority mismatch, routing-scope contradiction or active-state contradiction. No search-result ranking, filename recency, document prose, branch name or old gate completeness may repair the failure by inference.

## 7. Relationship to universal routing

This contract complements `OVC_VIT_UNIVERSAL_ROUTING_CONFORMANCE_CONTRACT_v0_1.md`:

- universal routing controls how eligible work reaches `PIP -> VIT -> SIQ`;
- current-state resolution controls how the system answers what VIT authority/state is current.

Both are required for the activated VIT substrate to be operationally trustworthy.

## 8. Rollback

Rollback is forward-only. Disable/supersede this stricter resolver while preserving all current and historical authority records, audit evidence and Git history. No historical record is rewritten.

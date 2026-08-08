# OC-G0 — OccurrenceContext Implementation Plan Ratification Gate

**Gate ID:** `OC-G0`  
**Title:** Standalone OccurrenceContext Implementation Plan v0.1 Ratification  
**Decision authority:** `OPERATOR_REQUIRED`  
**Plan:** `OVC-OCCURRENCE-CONTEXT-IMPLEMENTATION-PLAN-0.1`  
**Plan version:** `0.1`  
**Accepted design:** `OVC-OCCURRENCE-CONTEXT-DESIGN-SPEC-0.1`  
**Design decision:** `OC-D0 PASS / OPERATOR`  
**Design merge:** `2b348c92f3c6ac1831002f87f5d192d1046cb91b`  
**Design closeout/main baseline:** `dd03abb71361c7111af64f9f71e8ea28a436a8f4`  
**Plan branch:** `plan/occurrence-context-implementation-v0-1`  
**Status:** `GATE_READY`

## Decision requested

Ratify the implementation plan and grant only the bounded engineering authority needed to execute `OC-WP0` through `OC-WP5`, automatically ratifying and squash-merging wholly non-reserved PASS gates, while stopping at any newly discovered reserved authority boundary and at terminal `OC-G6`.

This decision does **not** start C2P.

## Current authority before decision

- OccurrenceContext design: `ACCEPTED_MERGED`.
- OccurrenceContext implementation: `NONE_PENDING_OC_G0`.
- Context `REPRESENTATION_INPUT`: `DENIED_BY_DEFAULT`.
- C2/C2E structural mutation: `DENIED`.
- C2E real-source replay: `DENIED_DEFERRED_AT_C2E2_G6`.
- New instrument/market/side/clock/lattice: `DENIED`.
- Validation occurrence/data access: `DENIED / LOCKED_UNCONSUMED`.
- MCARB scientific context admission: `NONE / DENIED`.
- Market-condition scientific vocabulary: `NONE / DENIED`.
- SFC reopening: `NOT_AUTHORIZED`.
- C2P: `NOT_STARTED / NOT_AUTHORIZED`.
- Selector/family/semantic/publication/probability/risk/exposure/execution/agent-write: `NONE` or `DENIED`.

## Proposed authority delta on PASS

`OC_WP0_TO_WP5_BUILD_TEST_READ_ONLY_SYNTHETIC_ONLY`

PASS authorizes only:

1. repository/source reconciliation and contract census;
2. contracts, schemas, versioned registries and compact synthetic fixtures;
3. deterministic canonical serialization, typed objects, identity/hash validation and append-only supersession;
4. synthetic/fixture/inactive deterministic OccurrenceContext construction and replay;
5. read-only adapters to already-existing C2/C2E/calendar/session/clock contracts without source replay or structural recomputation;
6. inert MCARB typed-reference/admission mechanics with `NO_SCIENTIFIC_ADMISSIONS` initially;
7. empty/inert market-condition vocabulary plumbing;
8. exact field-level consumer manifests and read-only Research Operations projection;
9. adversarial tests, C2/C2E hash/no-mutation proofs, QA and programme-state evidence;
10. automatic squash merge of intermediate non-reserved PASS packets after required checks and review-thread clearance.

## Explicitly denied after PASS

PASS does not authorize:

- C2P design or implementation;
- any C2/C2E structural contract change, ID/hash rewrite, boundary logic change or historical mutation;
- any context field as `REPRESENTATION_INPUT`;
- a new instrument, market, side, clock or lattice;
- real-source C2E replay or C2E activation;
- Validation occurrence/data access;
- scientific activation of MCARB AL/ET/VS/provider evidence;
- a new scientific market-condition/regime taxonomy;
- SFC reopening;
- C2.5/C3 semantic changes;
- selector activation/replacement;
- family/semantic/theory/candidate/model promotion;
- canonical/R2 publication or a new immutable release identity;
- probability, risk, exposure, trading, execution or agent-write authority;
- destructive deletion, force-push or history rewriting.

## Work sequence after PASS

```text
OC-WP0 repository/source reconciliation
  -> OC-G1 AUTO if non-reserved
OC-WP1 contracts/schema/registries/fixtures
  -> OC-G2 AUTO
OC-WP2 deterministic builder/supersession/replay
  -> OC-G3 AUTO
OC-WP3 C2/C2E/calendar/session/clock adapters
  -> OC-G4 AUTO only if existing semantics suffice
OC-WP4 inert MCARB typed-reference extension
  -> OC-G5 AUTO only with no scientific activation
OC-WP5 adversarial QA/read-only consumer integration
  -> OC-G6 OPERATOR_REQUIRED terminal conformance
STOP before C2P
```

## Acceptance conditions

A PASS accepts all of the following constraints:

1. implementation conforms to the already-accepted OC design and may not widen it silently;
2. `occurrence_key` remains structural-anchor-only;
3. context evolution remains append-only and forward-superseding;
4. C2/C2E source records are immutable read-only inputs;
5. context fields are non-structural by default;
6. `REPRESENTATION_INPUT` remains separately governed;
7. MCARB and market-condition scientific admission registries start empty/inert;
8. C2E adapters use typed contract fixture/inactive evidence only and do not reopen G6 real-source authority;
9. Validation remains hard-denied;
10. no new instrument/clock/side may enter the base implementation;
11. SFC remains deferred;
12. C2P remains outside this programme;
13. wholly non-reserved intermediate PASS gates may auto-ratify, commit, push and squash-merge;
14. any unexpected reserved delta forces an immediate operator stop;
15. terminal `OC-G6` is operator-required before later C2P design may rely on OccurrenceContext as an accepted upstream contract.

## Tests / QA required before decision

The plan PR must have:

- bounded changed-file inventory;
- plan QA recommendation `PASS`;
- complete repository suite `SUCCESS`;
- OVC profile assurance / FINAL_HEAD `SUCCESS`;
- compatibility / merge readiness `SUCCESS`;
- no unresolved blocking review thread.

## Warnings

- The design intentionally leaves exact first calendar/session/A-L registry bindings to WP0 reconciliation. WP0 must fail closed rather than invent boundaries.
- No completed MCARB benchmark result is automatically admitted by this plan.
- C2E remains terminally DEFERRED for real-source replay; this plan cannot use OC implementation as a route around that authority decision.
- A future need for a new session definition, instrument, clock, auxiliary scientific admission or representation-input role is an operator-required scope/authority change.

## Unresolved issues

No blocking issue is known at plan-ratification time. The following are explicitly deferred to WP0 evidence resolution without granting authority to invent semantics:

- exact calendar/session/A-L registry binding;
- exact compact provider/source descriptor allowlist;
- exact non-activating OC authority-state enum names where repository conventions require alignment;
- any future real MCARB admission;
- any future market-condition vocabulary;
- later SFC reopening sequence, if any;
- later C2E G6 supersession, if any.

## Rollback

`DEFER`, `BLOCK`, `QUARANTINE` or `SUPERSEDE` leaves the accepted OC design intact and grants no implementation authority. The plan branch/PR may remain as proposal evidence or be superseded by a new plan version; no runtime state has changed.

## Recommended decision

**PASS**.

The plan is deliberately engineered to keep `OC-WP0` through `OC-WP5` within deterministic build/test/read-only/synthetic authority and to stop before all known reserved scientific, structural, Validation and C2P boundaries.

## Exact work after PASS

1. Record `OC-G0 PASS` and bounded implementation authority.
2. Squash-merge the ratified implementation-plan PR if final-head checks remain green.
3. Record the merge receipt and current implementation state.
4. Create `build/oc-wp0-reconciliation` from the new lawful main.
5. Execute continuously through eligible auto-ratifiable packets.
6. Stop at an unexpected reserved boundary or terminal `OC-G6`.

## Exact operator command

`OVC APPROVE OC-G0 PASS`

Allowed decisions: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`.

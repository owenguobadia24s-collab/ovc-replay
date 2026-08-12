# ESLI-WP0 / ESLI-G0 materialisation

Programme: `OVC-OPTB-ESL-CONFORMANCE-v0.1`  
Plan: `OVC-OPTB-ESL-CONFORMANCE-IMPLEMENTATION-PLAN-0.1-REVISED-2`  
Gate: `ESLI-G0`  
Operator decision: `PASS`  
Execution baseline: `fa23baf4d57364aacef0b28635c54b43fd7dc9a9`

This packet materialises the operator-approved G0 decision, exact governing design/plan/evaluation identities, execution-time court-record census, requirement-to-artifact census, WP0 QA evidence and machine-readable programme state. It authorises only the bounded deterministic ESL conformance programme described by the ratified plan.

## Authority retained

No selector, C2/C2E/C2P/C2.5 semantic change, representation/topology/family promotion, StructuralTerm admission, C3 shadow/production activation, Validation consumption, publication, probability, risk, exposure, execution or agent-write authority is granted by this packet.

The execution-time court record differs from the planning snapshot in one material-but-nonblocking fact: C2E is now `ACTIVE_EXACT_NAMED_PACK_SCOPE_BOUND` under an operator-selected noncanonical pack. ESLI preserves that upstream authority and may reference it only where an exact ESL dependency declares it; this packet does not activate, replace or reinterpret C2E.

## Evidence

- `ESLI_GOVERNING_SOURCE_IDENTITIES.json` — exact SHA-256 source bindings.
- `ESLI_G0_DECISION.json` — operator PASS and bounded authority delta.
- `ESLI_WP0_COURT_RECORD_CENSUS.json` — main/PR/branch/upstream-state reconciliation.
- `ESLI_WP0_REQUIREMENT_ARTIFACT_CENSUS.json` — implementation gap classification.
- `ESLI_WP0_QA_PACKET.json` — WP0 assurance.
- `registries/implementation/esli/OVC_ESLI_STATE_v0_1.json` — programme state.
- `registries/implementation/esli/CURRENT_STATE_POINTER.json` — current-state pointer.

## Rollback

Before merge, close the bounded branch/PR. After merge, any correction must be forward/additive: preserve the G0 decision and exact source identities, supersede programme state with a corrective record, and do not rewrite history.

## Next packet

`ESLI-WP1` — common ESL contracts, schemas, registries and invariant runtime. It is auto-executable only within the ratified non-reserved authority envelope.

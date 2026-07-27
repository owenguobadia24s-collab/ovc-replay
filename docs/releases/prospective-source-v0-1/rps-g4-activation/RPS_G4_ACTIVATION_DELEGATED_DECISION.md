# RPS-G4 — Exact Binding Activation Delegated Decision

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Packet: `RPS-G4-ACTIVATION`
- Governing operator gate: `RPS-G4`
- Governing operator command: `OVC APPROVE RPS-G4`
- Governing decision merge: `b52fa297faa1b593fe9aaaf5d36a1b4e39a50eac`
- Activation baseline: `b52fa297faa1b593fe9aaaf5d36a1b4e39a50eac`
- Candidate branch: `activate/rps-g4-exact-binding-active-triage`
- Tested head: `e774932432f042f0eb43470f50a2147e0a5976af`
- Pull request: `#113`
- Decision: `PASS_ACTIVATION`
- Decision authority: `DELEGATED_IMPLEMENTATION_WITHIN_RPS_G4_OPERATOR_APPROVAL`
- QA: `PASS_ACTIVATION`

## Decision

Accept the fail-closed activation implementation for squash merge into `main`.

The packet materialises only the exact RPS-G4 authority delta:

- source binding `RPS.BINDING.32fb3003efa072916c11e907`;
- signing binding `RPS.SIGNING.50092c28981fef08f53a6cb5`;
- operator `OVC.OPERATOR.PRIMARY.LOCAL.V1`;
- bounded GBP/USD `ACTIVE_RESEARCH_TRIAGE`;
- one first PD-WP5 LIVE_PROSPECTIVE operation;
- mandatory stop at PD-G5.

## Runtime closure

The implementation distinguishes global triage readiness from candidate append eligibility.

The repository authority record enables `ACTIVE_RESEARCH_TRIAGE`, but begins with:

- `candidate_source_resolved=false`;
- `live_append_enabled=false`;
- evidence sequence `0`;
- first-operation limit `1`.

A candidate can become append-eligible only when it is genuinely `LIVE_PROSPECTIVE` and its immutable source lineage resolves. `TIME_GATED_REPLAY` remains non-evidentiary and cannot become append-eligible.

## Tests

- Activation workflow `30301205779`, job `90094300332`: PASS
- Canonical workflow `30301205665`, job `90094299926`: PASS

The tests cover exact identities, repository authority loading, fail-closed missing conditions, candidate-level gating, replay exclusion, cross-registry state, retained prohibitions and absence of private-key/raw-data/machine-path material.

## Authority retained

The activation grants no autonomous processing, automatic evidence creation, agent writes, active novelty ranking, semantic/family/theory promotion, C2E/C2.5/C3, selector/release/R2 mutation, Validation consumption, probability, risk, exposure, trading or execution authority.

## Corrected defect

The first activation run found a test-only registry-shape assumption: it required the identical readiness token in three registries that lawfully express readiness at different structural levels. The assertion was replaced with exact per-registry closure checks. No authority field, gate condition or acceptance threshold was weakened.

## Rollback

Set active triage false, clear the exact source and signing bindings, deny append and stop PD-WP5. Preserve source, compute, keys, signatures, rejected requests, append-only evidence, audits and quarantines.

## Continuation

After eligible squash merge:

1. record the activation merge SHA and effective service build hash;
2. create the bounded PD-WP5 packet from the new main tip;
3. prepare and, where externally possible, run exactly one operator-local LIVE_PROSPECTIVE operation;
4. stop at PD-G5 with complete evidence, or preserve command-ready work and stop at a concrete external-artifact blocker.

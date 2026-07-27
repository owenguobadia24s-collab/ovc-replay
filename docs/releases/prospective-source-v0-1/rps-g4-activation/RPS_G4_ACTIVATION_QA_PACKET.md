# RPS-G4 — Exact Binding Activation QA Packet

- Plan: `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- Activation packet: `RPS-G4-ACTIVATION`
- Governing gate: `RPS-G4`
- Operator decision: `PASS`
- Decision merge: `b52fa297faa1b593fe9aaaf5d36a1b4e39a50eac`
- Baseline main: `b52fa297faa1b593fe9aaaf5d36a1b4e39a50eac`
- Candidate branch: `activate/rps-g4-exact-binding-active-triage`
- QA recommendation: `PASS_ACTIVATION_CANDIDATE`

## Exact activation

The packet materialises only the authority explicitly granted at RPS-G4:

- source binding `RPS.BINDING.32fb3003efa072916c11e907`;
- signing binding `RPS.SIGNING.50092c28981fef08f53a6cb5`;
- operator `OVC.OPERATOR.PRIMARY.LOCAL.V1`;
- research line `RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1`;
- model `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`;
- one bounded PD-WP5 first LIVE_PROSPECTIVE operation;
- mandatory stop at PD-G5.

## Fail-closed runtime model

The authority model now separates programme-level triage activation from candidate-level append eligibility.

`ACTIVE_RESEARCH_TRIAGE` requires all of:

1. PD-G4 approved;
2. RPS-G4 approved;
3. the exact operator key bound;
4. the governed bridge healthy;
5. bounded human write authority true;
6. operation mode `LIVE_PROSPECTIVE`;
7. exact source binding present;
8. exact signing binding present;
9. explicit operator identity present.

A canonical append additionally requires immutable source lineage to resolve for the selected new candidate. The activation record intentionally sets `candidate_source_resolved=false` and `live_append_enabled=false`. This permits triage to start without enabling writes against replay, fixtures or unresolved candidates.

## Repository changes

- active authority record and schema;
- fail-closed authority loader and runtime model;
- Research Console authority loading when no runtime authority object is supplied;
- exact RPS, Pattern Discovery and C2 evidence registry updates;
- RPS-G4 and RPS-WP4 state closure;
- focused authority and cross-registry tests;
- dedicated activation workflow.

## Test matrix

The activation suite verifies:

- exact operator, source, signing, model and research-line identities;
- RPS-G4 decision merge provenance;
- repository authority loads as active triage;
- unresolved candidate append remains disabled;
- source-resolved LIVE_PROSPECTIVE candidate can become append-eligible;
- TIME_GATED_REPLAY can never become append-eligible;
- every missing global activation condition fails closed;
- first-operation limit is exactly one;
- replay backfill remains denied;
- novelty, semantic, selector, release, R2, Validation, probability, risk, exposure, trading, execution and agent authority remain absent;
- registries advance consistently to PD-WP5 and PD-G5;
- private-key material, raw market bytes and machine paths are absent.

## Authority assessment

This packet does not grant authority beyond the explicit RPS-G4 PASS. It merely materialises the exact approved delta. The activation remains narrower than unrestricted live operation:

- no candidate is currently source-resolved;
- no canonical append is enabled by the activation record alone;
- no provider request occurs;
- no replay output is relabelled or backfilled;
- no automatic evidence creation occurs;
- the first-operation limit is one;
- the next gate is PD-G5.

The activation packet is therefore eligible for delegated implementation and squash merge under the recorded operator decision, subject to passing focused and repository-wide tests with no unresolved review or blocking warning.

## Warnings

1. The June source is GAPPED and only supports the accepted readiness lineage.
2. The first PD-WP5 operation requires a genuinely new LIVE_PROSPECTIVE candidate after activation, not the June replay payload.
3. The operator private-key ACL remains externally attested.
4. `write_authority=true` denotes the already approved bounded human bridge; `live_append_enabled=false` remains the effective candidate-level write gate until immutable source resolution.

## Rollback

Set active triage false, clear source and signing bindings, deny LIVE_PROSPECTIVE append and stop PD-WP5. Preserve every source, compute, key, signature, compact evidence, rejected request, append-only evidence record, audit event and quarantine. Never rewrite or delete canonical evidence.

## Recommendation

`PASS_ACTIVATION_CANDIDATE` — merge after final tests, record the activation merge, then continue to the first incomplete PD-WP5 packet.

# OVC IROF Golden-2 Weekly End-to-End Assurance
## Implementation Plan v0.1

**Programme:** `OVC-IROF-GOLDEN2-WEEKLY-E2E-ASSURANCE-v0.1`  
**Plan:** `OVC-IROF-GOLDEN2-WEEKLY-E2E-ASSURANCE-IMPLEMENTATION-PLAN-0.1`  
**Baseline:** `main@cb77f01ff7a8db1f66c556edc94b8108b9e0ed01`  
**Operator admission:** `OVC RUN OVC-IROF-GOLDEN2-WEEKLY-E2E-ASSURANCE-v0.1`  
**Authority:** local synthetic fixture/generated execution only; authority effect NONE.

## 0. Decision

Execute a stronger second IROF golden run using one deterministic synthetic GBP/USD week generated at M1 for separate BID/ASK, aggregated through the existing lawful OPT-A clock machinery, transformed through the current C1 reference engine, revised C2 vNext components, synthetic-only C2E v0.2 lifecycle, SRI/comparability/distance/FDI/FamilyEvidenceStream, OccurrenceContext and Research Operations evidence surfaces.

This is a front-to-back integration assurance programme. It is not a scientific promotion programme and may not consume real-source C2E authority, Validation, a provider, an active selector, a promoted representation/family method, publication authority, probability, risk, exposure, execution or agent-write authority.

## 1. Court-record preflight

At admission:

- IROF v0.1 is `COMPLETED / INACTIVE_INFRASTRUCTURE_AVAILABLE`.
- OPT-A, C1 and revised C2 are current court-record implementations.
- C2E v0.2 synthetic execution is lawful; real-source replay remains separately owner-gated.
- SRI/FDI/FamilyEvidenceStream remain inactive conformance/evidence machinery and are lawful for synthetic assurance.
- OccurrenceContext remains nonstructural by default.
- Validation remains locked/unconsumed.
- Open PR #518 (Research Console), #517 (SRFD preparation), #516 (C2E real replay) and historical blocker/rehearsal PRs are proposal/evidence only and are not used as implementation authority.
- Historical draft PR #418 is not imported. Only scenario ideas may be independently re-expressed against current-main APIs.

## 2. Population contract

`PopulationSpec` intent:

- mode: `SYNTHETIC_GENERATED`;
- instrument: `GBPUSD`;
- native source grain: M1;
- sides: BID and ASK kept separate;
- interval: one complete synthetic calendar week covering Monday 00:00 UTC through the following Monday 00:00 UTC, with the current OVC GBPUSD calendar determining scheduled closure slots;
- source generation: deterministic, integer-tick path plus deterministic spread and volume;
- no hidden generator-truth field may enter OPT-A/C1/C2/C2E inputs;
- one explicit open-market gap and one incomplete interval are inserted to prove continuity reset and non-evaluability;
- generated market-like structure is fixture truth only and has no external market-evidence status.

Raw generated M1 rows remain runtime fixture material; only compact generator specification, hashes, counts and receipts belong in Git.

## 3. Execution DAG

The target executable subgraph is:

`SYNTHETIC_GENERATED -> OPT-A fixture/clock handling -> C1 -> revised C2 observation + structural projections -> synthetic C2E v0.2 -> OccurrenceContext -> SRI -> comparability/distance -> FDI/C2G -> FamilyEvidenceStream -> Research Operations`.

C2 structural execution must use current-main component APIs directly. Historical FSR wrappers are forbidden dependencies.

C2E must use a fixture-only frozen boundary pack and current v0.2 lifecycle APIs. It must not activate any boundary pack or claim empirical C2E suitability.

## 4. Work packets

### GOLDEN2-WP0 — admission, preflight and plan

Records this plan, exact main baseline, programme state and operator instruction. Gate `GOLDEN2-G0` is satisfied by the explicit named `OVC RUN` command because the admitted delta is synthetic-only and contains no reserved authority.

### GOLDEN2-WP1 — weekly source, C1 and revised-C2 execution

Implement a deterministic week generator and in-memory OPT-A adapter using current `Bar`/aggregation policy; build current C1 records with the current C1 reference engine; construct revised-C2 observations from exact C1 identities and execute current C2 structural components on deterministic checkpoints. Required evidence includes source counts, gaps, C1 counts, C2 observation/horizon/level/container/relation/formula/transition counts, chronology and separate-side assurance.

Auto gate `GOLDEN2-G1`.

### GOLDEN2-WP2 — C2E through Research Operations

Construct current C2E v0.2 input frames from actual Golden-2 revised-C2 outputs; execute synthetic lifecycle birth/continue/mutate/censor patterns through a fixture-only boundary pack; consume the resulting handoff through current SFC representation/comparison/FDI/evidence machinery; attach OccurrenceContext as stratification-only; project an IROF/Research Operations evidence object.

Auto gate `GOLDEN2-G2`.

### GOLDEN2-WP3 — deterministic replay, restart/cache, telemetry and closeout

Run fresh/repeated/alternate-order and checkpoint/resume equivalence, cache reuse/corruption quarantine, authority-denial checks and stage/whole-run telemetry. Emit a compact integrated result and programme closeout.

Auto gate `GOLDEN2-G3`.

## 5. Acceptance

PASS requires:

1. one generated synthetic week originates at OPT-A-shaped M1 BID/ASK observations;
2. C1 records are computed by the current C1 builder, not pre-baked;
3. revised-C2 observations and structural outputs are derived from those C1/source records;
4. C2E input frames are derived from the Golden-2 C2 outputs and current C2E lifecycle code executes synthetically;
5. the resulting current SFC/FamilyEvidenceStream and Research Operations surfaces complete;
6. source, C1, C2 and C2E counts/lineage are explicit;
7. `fresh == repeated == resumed == alternate-order` for the declared logical scientific result;
8. cache/checkpoint corruption quarantines rather than repairs;
9. BID/ASK are never collapsed;
10. OccurrenceContext is not consumed as `REPRESENTATION_INPUT`;
11. real source, provider intake, Validation, selectors, activation, publication, scientific promotion and exposure authorities remain untouched;
12. exact-head repository CI and OVC tiered assurance pass with no blocking review thread.

## 6. Scientific interpretation

A PASS proves software/contract integration and deterministic research execution over a controlled synthetic population. It does not establish market validity, representation adequacy, a valid empirical C2E boundary pack, stable family truth, or any predictive/exposure claim.

## 7. Rollback

Revert/supersede Golden-2-only generator/harness/tests/receipts/state. No upstream owner-stage source, selector, active pack, release, Validation record or scientific authority is rewritten.

## 8. Terminal state

Target: `COMPLETED / SYNTHETIC_WEEKLY_E2E_ASSURANCE_PASS` with current IROF v0.1 remaining completed/inactive infrastructure available.

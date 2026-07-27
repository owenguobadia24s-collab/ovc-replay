# PD-G2 — Trigger, Control and Novelty-Shadow Acceptance

## Gate identity

- Gate ID: `PD-G2`
- Governing plan: `OVC C2 Pattern Discovery and Review Layer v0.3`
- Governing source SHA-256: `03a4c602026950f3a496f6bf2085c378a62292090d334f3b0ea2f17f6463a0aa`
- Baseline main commit: `abc0f4dc63932907c331f645b17ec4cdd3bb58cf`
- Candidate branch: `build/pd-wp2-trigger-control-novelty`
- Candidate pull request: `#93`
- Prerequisite decision: `PD-G1 PASS`

## Completed packet

`PD-WP2 — Trigger, Control and Novelty-Shadow Engine`

Implemented:

- frozen structural, interaction, cross-scale, persistence and instability trigger evaluation;
- exact fired, not-fired and not-evaluable results;
- reason-coded first-valid source lineage;
- deterministic matched and population controls;
- explicit control-representation requirements and deficits;
- deterministic daily/family/depth backpressure;
- control reservation and explicit suppression reasons;
- baseline-forming novelty counts, frequency and raw distance;
- calibrated-shadow badges and hypothetical rank impact;
- zero actual novelty rank weight and no independent promotion;
- active novelty denial;
- named latency degradation states;
- compact fixtures, tests and CI.

## Current authority

- PD-G0: `APPROVED`.
- PD-G1 transition and CandidateWindow foundation: `APPROVED`.
- PD-WP2 implementation: candidate only pending this gate.
- Live Pattern Discovery processing: `NONE`.
- Active novelty ranking: `NONE`.
- Fingerprint and cluster authority: `NONE`.
- Evidence writes: `NONE`.
- Selector, release and R2 mutation: `DENIED`.
- C2E, C2.5, C3, Validation, probability, exposure, trading, execution and agent-write authority: `NONE`.

## Proposed authority delta

Accept the deterministic trigger evaluator, controls, queue backpressure and novelty-shadow implementation as derived inputs for `PD-WP3`.

This delta remains wholly inside the approved plan and is `AUTO-EXECUTABLE` because it:

- changes no selector, release or active market authority;
- performs no live prospective activation;
- grants no novelty ranking authority;
- creates no canonical evidence record;
- introduces no semantic, outcome, probability, exposure or execution authority;
- is entirely replaceable derived computation with a defined rollback.

## Acceptance conditions

1. Supported frozen triggers have positive, negative and not-evaluable coverage.
2. Every fired result has exact first-valid and source-transition lineage.
3. Cross-scale missing parent context fails as `NOT_EVALUABLE`.
4. Persistence and switching fire only on first threshold crossing.
5. Matched and population controls are deterministic.
6. Analytical control requirements and deficits are explicit.
7. Queue daily, family and hard-depth caps are deterministic.
8. Control slots are reserved before ordinary ranking.
9. Every overflow item has an exact `SUPPRESSED_*` reason.
10. `BASELINE_FORMING` exposes no badge and no ranking weight.
11. `CALIBRATED_SHADOW` changes no actual rank or promotion.
12. Active novelty activation fails with `OPERATOR_GATE_REQUIRED`.
13. Degradation states do not change chronology or discard records.
14. No outcome, probability, exposure, trade or execution dependency exists.
15. Focused, retained-foundation and canonical repository tests pass.

## QA

- QA packet: `docs/releases/pattern-discovery-v0-3/pd-wp2/PD_WP2_QA_PACKET.json`
- Final workflow IDs and candidate commit are filled only after the final candidate tip passes.

## Warnings and limitations

- No real C2 stream has been operated by this packet.
- Burn-in counters are implemented but no real novelty baseline has accumulated.
- The provisional Jaccard representation is not a PatternFingerprint.
- Recurrence and medoid-distance triggers remain non-promoting until PD-WP3 parents exist.
- Review Queue UI and evidence bridge remain PD-WP4.

## Changed files

- `contracts/research_operations/pattern_discovery/PATTERN_DISCOVERY_TRIGGER_CONTROL_AND_NOVELTY_SHADOW_CONTRACT_v0_1.md`
- `src/ovc/research_operations/pattern_discovery/evaluation.py`
- `src/ovc/research_operations/pattern_discovery/controls.py`
- `src/ovc/research_operations/pattern_discovery/novelty.py`
- `src/ovc/research_operations/pattern_discovery/backpressure.py`
- `src/ovc/research_operations/pattern_discovery/__init__.py`
- `fixtures/research_operations/pattern_discovery/pd_wp2/pd_wp2_cases.json`
- `tests/research_operations/pattern_discovery/test_pd_wp2_trigger_control_novelty.py`
- `.github/workflows/pd-wp2-trigger-control-novelty.yml`
- `registries/research_operations/pattern_discovery/PATTERN_DISCOVERY_IMPLEMENTATION_REGISTRY_v0_3.yaml`
- `docs/releases/pattern-discovery-v0-3/pd-wp2/*`

## External artifacts

No raw market data, full candidate stream, similarity matrix, cluster output, screenshot, canonical evidence record or R2 object was created.

## Rollback

Revert the bounded packet or delete and rebuild all derived trigger, control, novelty-shadow and queue-projection objects. Accepted PD-WP1, canonical C2, selectors, releases, existing evidence and R2 remain unchanged.

## Recommended decision

`PASS` after final CI.

Because the proposed delta is wholly non-reserved, a complete PASS with no blocking warning is eligible for delegated auto-ratification and squash merge. After integration, `PD-WP3` begins from the new lawful `main` tip.

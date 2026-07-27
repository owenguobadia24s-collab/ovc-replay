# PD-G0 — Pattern Discovery Design Freeze

## Gate identity

- Gate ID: `PD-G0`
- Title: Pattern Discovery authority, scale, mathematics, population, UI and evidence-bridge design freeze
- Governing plan: `OVC C2 Pattern Discovery and Review Layer v0.3`
- Governing source SHA-256: `03a4c602026950f3a496f6bf2085c378a62292090d334f3b0ea2f17f6463a0aa`
- Baseline commit: `3c0785ddb571a4af6de4bf5756a1dfae7e2d3557`
- Candidate branch: `build/pd-00-pattern-discovery-v0-3-freeze`
- Candidate commit: GitHub PR head at operator review time

## Completed packets

- `PD-00` — implementation-plan source binding and authority freeze.
- Scale, control sampling, capacity and backpressure contract.
- Deterministic PAM algorithm, distance and population decision.
- Novelty lifecycle, simple UI and OPT-A-bound price-strip contract.
- Evidence-bridge signing, idempotency, atomic audit and reconciliation contract.
- Candidate lifecycle failure-mode matrix.
- Typed schema candidates and trigger/implementation registries.
- Focused QA tests and dedicated CI workflow.

## Current authority

- Canonical C2 Discovery remains unchanged.
- C2 prospective evidence operation remains governed by the accepted C2-G7/C2 v0.2 contracts.
- Validation remains `LOCKED_UNCONSUMED`.
- Pattern Discovery has design-candidate authority only.
- C2E, C2.5, C3, OPT-C, OPT-D, probability, exposure, trading, execution and agent-write authority remain `NONE`.

## Proposed authority delta

Approve the frozen Pattern Discovery design and permit `PD-WP1` to implement the transition extractor and deterministic candidate-window engine on fixtures and approved read-only C2 inputs.

The proposed delta does **not** activate prospective processing, novelty ranking, clustering authority, the UI evidence bridge, evidence writes, selector changes or downstream model authority.

## Acceptance conditions

1. Every read, output, population and prohibited dependency is explicit.
2. Scale formula, latency objectives, queue caps, suppression and control comparability are frozen.
3. Candidate lifecycle and every named failure have exact fail-closed behaviour.
4. Trigger and completed fingerprints are separated; outcome fields are prohibited.
5. Deterministic PAM, composite distance, missingness, k selection, tie-breakers and capacity blocks are frozen.
6. Baseline, shadow and active novelty states have distinct authority; active ranking requires a later operator gate.
7. Queue, Candidate Detail and Clusters are the only v0.1 primary UI views; price data resolves to exact OPT-A lineage.
8. The evidence bridge is local, separately signed, idempotent, atomic and auditable; the UI holds no private key.
9. Discovery, human-reviewed and canonical-evidence populations remain distinct.
10. Focused and canonical repository tests pass on the candidate PR.

## Tests and QA

- Focused suite: `tests.research_operations.pattern_discovery.test_pd_g0_design_freeze`
- Canonical suite: `python -m unittest discover -s tests -p 'test_*.py'`
- Workflow: `.github/workflows/pd-g0-pattern-discovery-design-freeze.yml`
- Successful run: GitHub Actions `30254408829`
- Focused test step: `PASS`
- Canonical repository test step: `PASS`
- Diagnostic artifact upload: `PASS`
- QA result: `PASS_PD_G0_CANDIDATE`

## Warnings and limitations

- No Pattern Discovery runtime exists yet.
- PAM performance and arrival stability are specified but not yet implemented; they are acceptance work for PD-WP3/PD-G3.
- Novelty burn-in has not begun.
- No real candidate queue or evidence bridge has been operated.
- The optional browser shortcuts remain subject to Chrome/Windows compatibility and accessibility tests.
- Single-operator signing is acceptable only under the frozen local, sole-operator, descriptive boundary.
- Open PR #86 remains a separate stale-base Research Console candidate and is not absorbed by this packet.

## Unresolved issues

None inside PD-00 design scope. Runtime performance, trigger precision, operator efficiency and first-batch evidence remain later packet questions governed by their named gates.

## Changed files

- `.github/workflows/pd-g0-pattern-discovery-design-freeze.yml`
- `docs/implementation-plans/OVC_C2_PATTERN_DISCOVERY_AND_REVIEW_LAYER_v0_3_SOURCE_BINDING.md`
- `contracts/research_operations/pattern_discovery/PATTERN_DISCOVERY_AUTHORITY_CONTRACT_v0_3.md`
- `contracts/research_operations/pattern_discovery/PATTERN_DISCOVERY_SCALE_CONTROLS_AND_BACKPRESSURE_CONTRACT_v0_2.md`
- `contracts/research_operations/pattern_discovery/PD_CLUSTERING_ALGORITHM_AND_POPULATION_DECISION_v0_2.md`
- `contracts/research_operations/pattern_discovery/PATTERN_DISCOVERY_NOVELTY_UI_AND_PRICE_STRIP_CONTRACT_v0_1.md`
- `contracts/research_operations/pattern_discovery/C2_PATTERN_DISCOVERY_EVIDENCE_BRIDGE_AUTHORITY_CONTRACT_v0_2.md`
- `contracts/research_operations/pattern_discovery/PATTERN_DISCOVERY_FAILURE_MODE_MATRIX_v0_1.md`
- `schemas/research_operations/pattern_discovery/transition_and_trigger_v0_1.schema.json`
- `schemas/research_operations/pattern_discovery/candidate_window_v0_1.schema.json`
- `schemas/research_operations/pattern_discovery/fingerprint_and_cluster_v0_1.schema.json`
- `schemas/research_operations/pattern_discovery/append_request_v0_1.schema.json`
- `registries/research_operations/pattern_discovery/PATTERN_DISCOVERY_IMPLEMENTATION_REGISTRY_v0_3.yaml`
- `registries/research_operations/pattern_discovery/PATTERN_DISCOVERY_TRIGGER_REGISTRY_v0_1.yaml`
- `tests/research_operations/pattern_discovery/test_pd_g0_design_freeze.py`
- `docs/releases/pattern-discovery-v0-3/PD_G0_OPERATOR_GATE_PACKET.md`

## External artifacts and hashes

- Governing DOCX: SHA-256 `03a4c602026950f3a496f6bf2085c378a62292090d334f3b0ea2f17f6463a0aa`, 60,117 bytes.
- No raw market data, candidate stream, fingerprint store, similarity matrix, screenshot or R2 object was created.

## Rollback

Close the candidate PR or reset the unmerged branch reference. Main, active C2 selectors, releases, evidence records and R2 remain unchanged. No destructive action is required.

## Recommended decision

`PASS`

The design packet is complete, the focused PD-G0 assertions pass and the canonical repository suite passes. Approval remains an operator authority decision.

## Exact work that begins automatically after approval

`PD-WP1` starts on a new bounded branch from the approved baseline. It will implement TransitionRecord extraction, TriggerEvent persistence, candidate deduplication, deterministic open/accumulate/close behaviour, gap/quarantine/selector failure transitions, fixtures, tests and the `PD-G1` operator packet. It will stop at `PD-G1` and will not activate live prospective processing.
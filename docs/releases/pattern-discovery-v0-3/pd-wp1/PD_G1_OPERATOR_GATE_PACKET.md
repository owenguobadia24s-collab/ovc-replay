# PD-G1 — Transition and Candidate-Window Acceptance

## Gate identity

- Gate ID: `PD-G1`
- Governing plan: `OVC C2 Pattern Discovery and Review Layer v0.3`
- Governing source SHA-256: `03a4c602026950f3a496f6bf2085c378a62292090d334f3b0ea2f17f6463a0aa`
- Baseline commit: `d567297b1743d665e603e62e258767b18f2694ee`
- Candidate branch: `build/pd-wp1-transition-candidate-engine`
- Candidate commit: `TO_BE_RESOLVED_AT_PR_TIP`
- Prerequisite decision: `PD-G0 PASS`

## Completed packet

`PD-WP1 — Transition and Candidate-Window Engine`

Implemented:

- exact C2 source-binding adapter;
- deterministic five-axis and structural-context TransitionRecords;
- first-valid chronology enforcement;
- deterministic TriggerEvents bound to existing transitions;
- append-only derived JSONL ledgers and duplicate denial;
- display-only trigger precedence;
- deterministic CandidateWindow identity, deduplication and trigger snapshot;
- compatible-trigger attachment and incompatible-closure separation;
- explicit per-family and per-instrument cap suppression;
- open, accumulate, pending-input, resume, close and invalid lifecycle;
- gap, quarantine, context-change and selector-change failure handling;
- synthetic fixtures, focused tests and dedicated CI.

## Current authority

- `PD-G0` design freeze: `APPROVED`.
- PD-WP1 implementation: candidate only.
- Pattern Discovery live prospective processing: `NONE`.
- Trigger-registry runtime evaluation: `NONE`.
- Novelty ranking: `NONE`.
- Fingerprint and cluster authority: `NONE`.
- Evidence bridge and evidence writes: `NONE`.
- C2E, C2.5, C3, Validation consumption, probability, exposure, trading, execution and agent-write authority: `NONE`.

## Proposed authority delta

Approve the deterministic transition and CandidateWindow implementation as the accepted derived foundation for `PD-WP2`.

After PASS, `PD-WP2` may implement the frozen structural, cross-scale, persistence, recurrence and control trigger engine plus novelty baseline formation in non-authoritative shadow mode.

This gate does not activate live prospective processing, novelty ranking, clustering, evidence writes, selectors, releases or downstream market authority.

## Acceptance conditions

1. The same source pair produces identical ordered TransitionRecords and IDs.
2. Mixed source bindings and non-increasing chronology fail closed.
3. TriggerEvents bind existing transitions and persist append-only.
4. Display precedence preserves every TriggerEvent.
5. Compatible triggers attach to one candidate; incompatible closure profiles remain distinct subject to caps.
6. Every cap suppression is retained with an exact reason.
7. The trigger snapshot hash cannot change after later accumulation.
8. Gap, quarantine, pending-input, context-change and selector-change paths match the frozen failure matrix.
9. Candidate outputs contain no outcome, probability, trade, exposure or execution fields.
10. Focused, retained-boundary and canonical repository tests pass.

## Tests and QA

- Focused suite: `tests.research_operations.pattern_discovery.test_pd_wp1_transition_candidate_engine`
- Retained boundary: `tests.research_operations.pattern_discovery.test_pd_g0_design_freeze`
- Canonical suite: `python -m unittest discover -s tests -p 'test_*.py'`
- Workflow: `.github/workflows/pd-wp1-transition-candidate-engine.yml`
- Result: `PENDING_GITHUB_CI`
- QA packet: `docs/releases/pattern-discovery-v0-3/pd-wp1/PD_WP1_QA_PACKET.json`

## Warnings and limitations

- The full trigger registry is not evaluated by PD-WP1.
- No live C2 stream has been consumed by Pattern Discovery.
- Candidate windows have not been ranked or displayed in the console.
- Fingerprints, novelty and clustering remain unimplemented.
- Transition and trigger JSONL stores are derived and replaceable, not canonical evidence.
- The evidence bridge remains specification-only.

## Changed files

- `src/ovc/research_operations/pattern_discovery/__init__.py`
- `src/ovc/research_operations/pattern_discovery/models.py`
- `src/ovc/research_operations/pattern_discovery/transitions.py`
- `src/ovc/research_operations/pattern_discovery/triggers.py`
- `src/ovc/research_operations/pattern_discovery/persistence.py`
- `src/ovc/research_operations/pattern_discovery/windows.py`
- `src/ovc/research_operations/pattern_discovery/engine.py`
- `contracts/research_operations/pattern_discovery/PATTERN_DISCOVERY_TRANSITION_AND_WINDOW_ENGINE_CONTRACT_v0_1.md`
- `fixtures/research_operations/pattern_discovery/pd_wp1/c2_state_stream.json`
- `tests/research_operations/pattern_discovery/test_pd_wp1_transition_candidate_engine.py`
- `.github/workflows/pd-wp1-transition-candidate-engine.yml`
- `docs/releases/pattern-discovery-v0-3/pd-wp1/PD_WP1_IMPLEMENTATION_SUMMARY.md`
- `docs/releases/pattern-discovery-v0-3/pd-wp1/PD_WP1_QA_PACKET.json`
- `docs/releases/pattern-discovery-v0-3/pd-wp1/PD_G1_OPERATOR_GATE_PACKET.md`
- `registries/research_operations/pattern_discovery/PATTERN_DISCOVERY_IMPLEMENTATION_REGISTRY_v0_3.yaml`

## External artifacts and hashes

No raw market data, full candidate stream, screenshot, similarity matrix, cluster output, canonical evidence record or R2 object was created.

## Rollback

Abandon the unmerged PD-WP1 candidate branch and rebuild replaceable derived artifacts from the approved source. Main, canonical C2, active selectors, releases, evidence and R2 remain unchanged.

## Recommended decision

`PASS` only after all named CI checks are green. Otherwise `BLOCK` on the exact failing assertion.

## Exact work beginning after approval

`PD-WP2` will start on a new bounded branch. It will implement the frozen trigger registry, deterministic control sampling, baseline-forming novelty measurements, backpressure metrics, fixtures, QA and the `PD-G2` operator packet. Active novelty ranking will remain prohibited.

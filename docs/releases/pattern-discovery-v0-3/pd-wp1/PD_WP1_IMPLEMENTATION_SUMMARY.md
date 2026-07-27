# PD-WP1 — Transition and Candidate-Window Engine

## Status

`IMPLEMENTED_AWAITING_PD_G1`

## Governing plan

- Plan: `OVC C2 Pattern Discovery and Review Layer v0.3`
- Source SHA-256: `03a4c602026950f3a496f6bf2085c378a62292090d334f3b0ea2f17f6463a0aa`
- Approved prerequisite: `PD-G0`
- Packet baseline: `d567297b1743d665e603e62e258767b18f2694ee`
- Branch: `build/pd-wp1-transition-candidate-engine`

## Implemented capability

- strict C2 snapshot adapter for exact release, manifest, selector, clock, side, scope and parameter-pack binding;
- deterministic TransitionRecord extraction across all five C2 axes and structural-context references;
- strict first-valid chronology and mixed-binding denial;
- deterministic TriggerEvent construction from existing transitions;
- append-only JSONL persistence with duplicate identity rejection;
- display-primary trigger precedence without event removal;
- deterministic CandidateWindow identity and trigger-time snapshot hash;
- compatible-trigger attachment and incompatible-closure separation;
- per-family/scope and per-instrument open-window caps with explicit suppression records;
- open, accumulate, pending-input, resume, close and invalid lifecycle operations;
- exact gap, quarantine, context-change and selector-change failure transitions;
- fixture-only composition service and synthetic C2 state stream;
- focused tests and dedicated GitHub Actions workflow.

## Authority boundary

The implementation operates only on fixtures and approved read-only C2 records. It does not activate the Pattern Discovery prospective job, evaluate the full trigger registry, calculate novelty, build fingerprints or clusters, populate the Research Console, append canonical evidence, mutate selectors or releases, write R2, or introduce C2E, C2.5, C3, probability, exposure, trading, execution or agent authority.

## Determinism and chronology

Transition and trigger identities use canonical SHA-256 material excluding local path, run time and machine state. Candidate trigger snapshots contain only the C2 and trigger material available at the exact trigger first-valid timestamp. Later accumulation cannot alter the trigger snapshot hash.

## Persistence

TransitionRecord and TriggerEvent JSONL ledgers are append-only, duplicate-safe and replaceable. CandidateWindow objects are derived runtime/read-model objects. None is canonical evidence.

## Fixtures

`fixtures/research_operations/pattern_discovery/pd_wp1/c2_state_stream.json` includes stable and changing C2 axes, relation-set movement, an explicit source gap, an explicit quarantined source and exact release lineage.

## Tests

- Focused: `python -m unittest tests.research_operations.pattern_discovery.test_pd_wp1_transition_candidate_engine`
- Retained boundary: `python -m unittest tests.research_operations.pattern_discovery.test_pd_g0_design_freeze`
- Canonical: `python -m unittest discover -s tests -p 'test_*.py'`

Final GitHub CI evidence is recorded in the PD-G1 packet before an operator decision is requested.

## Rollback

Abandon the unmerged candidate branch and rebuild the replaceable derived artifacts from the approved sources. Main, canonical C2, selectors, releases, evidence records and R2 remain unchanged.

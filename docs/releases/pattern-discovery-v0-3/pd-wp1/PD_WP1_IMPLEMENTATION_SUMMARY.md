# PD-WP1 — Transition and Candidate-Window Engine

## Status

`GATE_READY_PD_G1`

## Governing plan

- Plan: `OVC C2 Pattern Discovery and Review Layer v0.3`
- Source SHA-256: `03a4c602026950f3a496f6bf2085c378a62292090d334f3b0ea2f17f6463a0aa`
- Approved prerequisite: `PD-G0`
- Packet baseline: `d567297b1743d665e603e62e258767b18f2694ee`
- Candidate implementation commit: `7b16174656f9370d13ff4e3575b6834513705892`
- Branch: `build/pd-wp1-transition-candidate-engine`
- Pull request: `#90`

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
- additive registration of the approved Pattern Discovery Python namespace;
- focused tests and dedicated GitHub Actions workflow.

## Authority boundary

The implementation operates only on fixtures and approved read-only C2 records. It does not activate the Pattern Discovery prospective job, evaluate the full trigger registry, calculate novelty, build fingerprints or clusters, populate the Research Console, append canonical evidence, mutate selectors or releases, write R2, or introduce C2E, C2.5, C3, probability, exposure, trading, execution or agent authority.

## Determinism and chronology

Transition and trigger identities use canonical SHA-256 material excluding local path, run time and machine state. Candidate trigger snapshots contain only the C2 and trigger material available at the exact trigger first-valid timestamp. Later accumulation cannot alter the trigger snapshot hash.

## Persistence

TransitionRecord and TriggerEvent JSONL ledgers are append-only, duplicate-safe and replaceable. CandidateWindow objects are derived runtime/read-model objects. None is canonical evidence.

## Fixtures

`fixtures/research_operations/pattern_discovery/pd_wp1/c2_state_stream.json` includes stable and changing C2 axes, relation-set movement, an explicit source gap, an explicit quarantined source and exact release lineage.

## Tests and QA

- Focused suite: `PASS`
- Retained PD-G0 boundary suite: `PASS`
- Canonical repository suite: `PASS`
- Dedicated workflow: `30258601276` — `SUCCESS`
- Canonical workflow: `30258601125` — `SUCCESS`
- Retained PD-G0 workflow: `30258601144` — `SUCCESS`
- QA result: `PASS_PD_G1_CANDIDATE`

One correctable canonical namespace-allowlist failure was found and resolved inside packet scope. The approved `ovc.research_operations.pattern_discovery` namespace was added to the Research Operations namespace registry and canonical test allowlist, then all affected and repository-wide tests were rerun successfully.

## Rollback

Abandon the unmerged candidate branch and rebuild the replaceable derived artifacts from the approved sources. Main, canonical C2, selectors, releases, evidence records and R2 remain unchanged.

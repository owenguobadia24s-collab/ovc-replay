# C2AR-WP5.5 Synthetic Pipeline Topology Contract v0.1

Programme: `OVC-C2-ANATOMY-REDESIGN-v0.2`  
Packet: `C2AR-WP5.5`  
Gate: `C2AR-G5.5`  
Authority: `SHADOW_ONLY`

## Purpose

Prove the complete observation → horizon → level → container → relation topology before operator-required integrated freeze at CEAR-G6. The smoke uses one compact synthetic GBP/USD BID fixture and mocked inactive selectors/projections. It is not market evidence and cannot select formulas, thresholds, parameters or authority.

## Required topology

1. Enumerate all fixed-clock observations with exact first-valid chronology.
2. Evaluate one causal trailing horizon without future members.
3. Construct candidate evidence, confirmed pivot levels, trailing range levels and a complete swing graph.
4. Construct a trailing measurement container and explicit-pairing swing envelope.
5. Build complete raw relation inventories and fixed-object crossing evidence.
6. Exercise inactive level and container projections with visible candidates, ties, exclusions and nullable selections.
7. Emit one deterministic manifest with per-stage hashes and a final manifest SHA-256.

## Invariants

- Two identical executions from the same fixture produce byte-identical logical manifests and SHA-256 values.
- Every downstream object references upstream immutable IDs; no object is silently copied under a new authority.
- No level or container is first-valid after the current observation.
- The horizon contains no future member.
- Ambiguity, censorship, no-match and exclusions remain explicit.
- Mock selectors and projections have `active=false`, `canonical=false`, and no fallback.
- No active selector, parameter, formula, threshold, semantic promotion, release, publication, Validation, C2E, C2.5, C3, probability, risk, exposure, trading, execution or agent-write authority.
- Fixture bytes are synthetic and compact; no provider or raw market data is added.

## Failure behaviour

Any missing stage, nondeterministic hash, future member, incompatible interface, hidden selection, missing exclusion, unexpected authority or incomplete candidate ledger is `BLOCK`. Do not weaken earlier frozen contracts or silently alter the smoke fixture.

## Rollback

Delete and rebuild smoke manifests and projections. Preserve the fixture, contract, test evidence, QA, decision and all CEAR-G1 through CEAR-G5 normative boundaries.

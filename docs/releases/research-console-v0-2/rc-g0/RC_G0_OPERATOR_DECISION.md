# RC-G0 Operator Decision

Programme: OVC Research Console v0.2  
Gate: RC-G0 — UI contract and preflight review  
Decision: **PASS**  
Reviewed RC-00 merge: `2e7f88e2a42e3feba4b4c1c7a2ea448e0a6b5b01`  
Reviewed RC-00 head: `f8c3b1786488b0847192cce3f69a7782d82fc72d`

## Decision

The Research Console v0.2 preflight and UI contracts are accepted for bounded implementation.

RC-WP1 — Design system, shell and navigation is authorised with **local presentation capability only**. RC-WP1 may implement the shared application shell, visual tokens, navigation, context bar, authority strip, reusable cards, status badges, source-reference components and fixture-only route rendering.

## Findings

- all planned routes have stable IDs, source families, read-only authority and fallback behaviour;
- no-signal health cannot be treated as PASS;
- unknown statuses fail closed;
- unregistered actions are prohibited;
- the visual Deploy control is replaced with a non-clickable LOCAL badge;
- repository, release, selector, threshold and market-model mutation remain prohibited;
- research-session and research-record creation remain deferred;
- canonical GitHub Actions tests passed on the reviewed RC-00 head;
- RC-00 was squash-merged to main without force push.

## Authority granted

`RC-WP1_DESIGN_SYSTEM_SHELL_AND_NAVIGATION`

This grants fixture-only local presentation work. It does not authorise live operational projections or research interpretation.

## Authority denied

- live read-model v0.2 projections pending RC-G2;
- live Research Desk, Replay and Evidence data pending RC-G3;
- research-record creation pending a separate write-authority gate;
- repository, selector, threshold, release or market-classification mutation;
- probability, exposure, trading, execution or agents;
- cloud or remote deployment.

## Next gate

RC-G1 — shell and navigation acceptance, after RC-WP1 completes and all planned routes render from valid, empty, WARN and BLOCK fixtures at the approved viewport widths.

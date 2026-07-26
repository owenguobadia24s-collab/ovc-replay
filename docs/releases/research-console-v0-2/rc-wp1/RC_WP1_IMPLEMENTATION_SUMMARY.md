# RC-WP1 Implementation Summary

Programme: OVC Research Console v0.2  
Work package: RC-WP1 — Design system, shell and navigation  
Branch: `build/research-console-v0-2-shell-navigation`  
Base commit: `e4fdc03014b1f133b32cd7a921142b4354079fe4`  
Disposition: `COMPLETE_RC_G1_REVIEW_READY`

## Implemented

- replaced the raw single-page presentation with a shared dark application shell;
- added stable grouped navigation for all fourteen frozen v0.2 route IDs;
- added a persistent context bar, authority strip and non-clickable `LOCAL · NO DEPLOY` treatment;
- added reusable metric, status, empty-state and source-reference components;
- added valid, empty, WARN and BLOCK fixtures for every route;
- preserved the existing read-model identity as bounded shell context only;
- removed the former hard stop when the local read model is missing or malformed;
- added tests that compare the shell route model with the frozen route registry and enforce the no-mutation boundary.

## Authority boundary

RC-WP1 adds local presentation capability only. Route contents are fixtures. Live v0.2 summaries and operational projections remain denied until RC-G2. Live Research Desk, Replay and Evidence data remain denied until RC-G3. Research-record creation remains denied pending a separate write-authority gate.

The console exposes no repository, selector, threshold, release, classification, probability, exposure, execution, agent or remote-deployment action.

## v0.3 disposition

The OVC Research Console v0.3 unified-workspaces plan is deferred and not adopted by this branch. RC-WP1 follows the accepted v0.2 route, card, status, empty-state and action contracts. A future v0.3 programme would require a separate amendment gate because it changes the accepted information architecture.

## RC-G1 review requirements

RC-G1 should verify:

1. all fourteen routes render in VALID, EMPTY, WARN and BLOCK fixture modes;
2. the shell remains usable at 1280×720, 1440×900 and 1920×1080;
3. status is not communicated by colour alone;
4. no empty or missing state implies PASS;
5. the exact represented source commit and read-model hash remain visible;
6. no mutation or deployment control is present;
7. canonical repository tests and RC-WP1 tests pass on the reviewed branch head.

## Next gate

`RC-G1 — shell and navigation acceptance`

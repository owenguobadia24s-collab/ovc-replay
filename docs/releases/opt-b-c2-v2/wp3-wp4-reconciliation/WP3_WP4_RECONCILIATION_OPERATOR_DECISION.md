# OPT-B.C2 v2 WP3-WP4 actual-parent reconciliation

**Decision: PASS actual C1 primitive handoff and exact OPT-A price-parent engine trust.**

The earlier WP3-WP4 engine trusted a synthetic envelope that embedded absolute prices and precomputed range/swing fields in C1. The published C1 release lawfully contains neither. It contains the frozen atomic primitives and exact links to the OPT-A source row.

This reconciliation:

- preserves the immutable C1 releases unchanged;
- verifies the complete exact OPT-A release before resolving a price row;
- joins by role, release, manifest, manifest SHA-256, source path, timestamp and source-bar ID;
- proves current-bar C1 primitives agree with the resolved OHLC;
- derives rolling ranges, midpoints and confirmed swings from chronological exact parents;
- enforces first-valid chronology, gap reset and scope-bound persistence;
- implements local 15M, local 2H and 15M-with-latest-first-valid-2H scopes;
- keeps all parameters in the frozen C2 parameter pack.

The engine is trusted against fixtures shaped exactly like the published parents. No actual Discovery or Development replay is claimed in this packet because the exact OPT-A release roots were not mounted in the execution environment.

C2 candidate release, publication, selector and activation remain `NONE`. Validation remains `LOCKED_UNCONSUMED`. Probability, exposure, trading and execution remain `NONE`.

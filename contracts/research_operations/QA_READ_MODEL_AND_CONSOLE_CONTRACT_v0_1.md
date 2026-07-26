# QA, Read Model and Console Contract v0.1

## Status

`IMPLEMENTED_FOR_REVIEW — NOT ACTIVE`

## Authority boundary

RO-WP3 may compute deterministic QA assertions, build replaceable typed indexes from approved compact artifacts, and render those indexes through a local read-only console.

It may not:

- rewrite source records or artifacts;
- repair a failed assertion silently;
- traverse unapproved paths;
- consume Validation payloads;
- mutate Git, R2, selectors, releases, thresholds or parameter packs;
- create market classifications, probability, exposure, trading, execution or agent authority.

## QA runner

A QA run receives a target by value, executes registered checks and verifies that the target's canonical hash is unchanged. Assertions use `PASS`, `WARN`, `BLOCK`, `QUARANTINE` or `NOT_EVALUATED`. A blocking assertion blocks the run; the runner does not repair the target.

## Typed read model

The read model is a replaceable derived artifact. It stores source commit, catalogue identity, object identity, status, authority, portable source references, lineage and multidimensional health signals. Rebuilding from the same logical compact inputs produces the same logical hash. Deleting the index removes no authority.

Missing, stale, conflicted, quarantined and not-evaluable states remain visible. No unavailable field is converted to neutral.

## Console

The console consumes only the typed read model. It is bound to `127.0.0.1` by the Windows launcher and exposes source commit and read-model hash. It provides no direct write control. Approved research writes continue through the governed RO-WP2 CLI and append-only service.

## Review state

Implementation does not activate these surfaces. Activation requires an operator review of the exact branch inventory and passing canonical tests. Validation remains `LOCKED_UNCONSUMED`.

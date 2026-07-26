# OPT-B.C1 v2 WP5 trigger reconciliation

The original bounded execution request was present on `build/opt-b-c1-v2-wp5-dispatch`, but no publication receipt or bot reconciliation commit appeared on `main`.

This reconciliation broadens only the dispatcher event surface so the exact execution-request pull request can trigger the canonical `workflow_dispatch` entrypoint on `main`. Publication scope, exact WP4F artifact bindings, R2 target keys, full-byte verification, selector state, C2 denial and Validation lock remain unchanged.

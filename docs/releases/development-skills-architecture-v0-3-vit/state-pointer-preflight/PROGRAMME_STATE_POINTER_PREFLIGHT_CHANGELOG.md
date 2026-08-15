# Change summary

- Adds a deterministic read-only programme-state/current-pointer consistency library.
- Adds a CLI intended to run before expensive exact-head assurance.
- Adds focused regression tests for stale pointers, missing state, completed-successor contradictions and legacy-schema non-inference.
- Binds `PROGRAMME_STATE_POINTER_CONSISTENT` into the active default DSAI3V execution-substrate assurance list.
- No authority expansion; no state mutation; no parallel physical merge.

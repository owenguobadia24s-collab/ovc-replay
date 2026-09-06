# RRSCG Core WP1 — exact-final conformance repair v0.1

The first exact-final repository run exposed two repository-integration defects, neither of which changed or falsified the R2 kernel: the new inactive RRSCG package had not yet been added to the repository namespace census, and the exact-source function-body oracle used `ast.dump()` fingerprints generated under a different Python runtime than CI.

This repair is deliberately forward-only. `LSIAC_PROGRAMME_STATE_v0_22.json` remains the immutable historical record of the earlier source-byte blocker. `LSIAC_PROGRAMME_STATE_v0_24.json` is a new current state, and `records/research_operations/lsiac/CURRENT_STATE_POINTER.json` names it explicitly. No historical state is deleted or rewritten.

For algorithmic assurance, the exact bound R2 archive at SHA-256 `5426cd9340c93a2aff0f5c8f3093f9db876647d1790aaa82da3e444a4f3029b5` is used to generate exact UTF-8 source-segment SHA-256 fingerprints for the same 20 load-bearing top-level functions. This removes Python-version serialization variance while strengthening the comparison from runtime-specific AST serialization equality to exact function-source equality. The historical AST oracle is retained as evidence and is not rewritten.

Authority delta is `NONE`. RRSCG remains inactive. Capability activation, active discovery/development/validation, selector replacement, semantic promotion, publication, probability/risk/exposure/E-H/trading/execution and agent-write authority remain denied.

# GRT Current-State Policy v0.1

**Status:** `PROPOSED_UNADMITTED`  
**Authority effect:** `NONE_PRE_ENFORCEMENT`

Currentness is a typed lifecycle and source-binding fact, not a filename convention.

Each governed current-state role declares an exact obligation ID, allowed artifact classes, cardinality, whether a source binding is mandatory, and its stale-state policy. A missing mandatory current-state projection is not repaired by choosing the most recently modified file. Historical records remain immutable and addressable.

Required rules:

- exactly one active programme-state projection where a programme declares a current state;
- current design/plan/release/authority pointers are source-bound when present;
- immutable decision records remain historical authority evidence rather than mutable current documents;
- rebuildable read models never become durable authority;
- ambiguous or stale current-state roles fail closed after activation;
- before G3, all outputs are advisory or candidate evidence only.

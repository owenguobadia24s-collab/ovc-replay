# OccurrenceContext Consumer Contract v0.1

Every consumer MUST supply a versioned `ContextConsumptionManifest` naming consumer kind/version, accepted context schema/pack, exact field paths, dependency disposition (`REQUIRED|OPTIONAL|FORBIDDEN`), intended base role (`STRATIFIER|FILTER|DISPLAY_ONLY`) or separately governed representation admission, admissible first-valid cutoff, missingness behavior, and manifest hash.

Whole-envelope opportunistic consumption is forbidden. Undeclared fields MUST fail closed.

SRI may use context for provenance/stratification only. FDI/family algorithms may not read OccurrenceContext directly. Future C2P may reference a context ID as non-identity annotation only and is not implemented by this programme. Revised C2.5 and future C3 must declare exact context field dependencies; default is no context dependency. Research Operations may project context read-only and expose lineage/missingness but may not mutate structural evidence.

Any consumer use as `REPRESENTATION_INPUT`, any semantic/event predicate change, or any authority delta reserved by the plan requires separate operator-governed admission.
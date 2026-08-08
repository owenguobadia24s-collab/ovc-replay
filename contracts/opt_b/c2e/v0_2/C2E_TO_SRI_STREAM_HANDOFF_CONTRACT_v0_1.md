# C2E -> SRI Stream Handoff Contract v0.1

WP0 found no repository-authoritative SRI implementation contract at the C2E2 execution baseline. Therefore this producer contract freezes only C2E-owned stable read fields and imports no SRI/FDI authority.

A read-only handoff exposes: episode ID; boundary-pack ID; source-release identity; instrument/side/scope/scale; lifecycle status; immutable genesis reference; latest lawful snapshot reference; phase, boundary, lineage and membership references; availability/missingness state; first-valid time; record/logical hashes and source lineage where present.

C2E does **not** own or emit representation vectors, normalization, distance/similarity, family/cluster/medoid assignment, sensitivity, invariant-core status, C3 semantics, outcomes, forecasts or exposure attributes. A consumer may derive those only under its own separately governed contract.

`C2ERemapRecord` is never a canonical SRI key: `comparison_only=true` is mandatory and remap may not become episode identity, lineage or causal parentage.

Authority remains `READ_ONLY_PRODUCER_HANDOFF`; no downstream write or activation route exists.

# OVC Shared Systems Evidence, State, Lineage and Interface Contract v0.1

Status: inactive/reference constitution under `SHSI-WP2`; authority effect `NONE`.

`EvidenceFrontier` records the exact evidence lawfully available to an owner evaluation
at one UTC cutoff. It is not a stream cursor, checkpoint or replay position. Evidence
after the cutoff fails closed. Missing required and optional dependencies remain typed,
and affect only each descriptor's declared dependent surfaces.

`DependencyDescriptor` keeps requiredness, consumption permission and failure
disposition as separate axes. `REQUIRED`, `FORBIDDEN` and warning/degradation outcomes
must never be packed into a single lifecycle token.

`StateVector` is a set of owner-scoped `StatePlaneValue` objects. Lifecycle,
availability, observability, evaluability, comparability, execution, authority,
maturity/progression and assurance/reproducibility are orthogonal. No value implies a
value on another plane without an exact owner rule. Research Operations legacy
`authority_state=FROZEN` is preserved as record-governance history and maps to
`AUTHORITY=UNKNOWN` unless a separate authority decision is bound.

`LineageEdgeEnvelope` owns envelope structure only. Predicate meaning remains with the
registered owner. The bare predicate `PARENT` is forbidden. Unknown extension types or
owner predicates fail closed.

`InterfaceBinding` binds exact producer/consumer contracts, schemas, serialization
profiles and generations. Normative `latest` references are forbidden.
`CompatibilityContract` classifications are explicit. `AdapterDescriptor` may only
rename, reshape or project declared source fields; every dropped field is declared and
semantic invention is forbidden.

These contracts do not change a domain record, current consumer path, owner, source or
research role; do not consume Validation; and grant no scientific, semantic,
publication, probability, risk, exposure or execution authority.

# IROF Stage Adapter and DAG Contract v0.1

Status: INACTIVE ENGINEERING CONTRACT. Authority effect: NONE.

## Purpose

Define the deterministic, semantics-neutral planning boundary between an IROF PipelineProfile and stage-specific implementations. The generic planner may inspect only StageSpec metadata, dependency declarations, typed input/output envelopes and execution-control metadata. It may not inspect scientific payload values to infer hidden dependencies or alter scientific meaning.

## Canonical DAG rules

1. Each included stage ID resolves to exactly one StageSpec.
2. REQUIRED dependencies must be present in the profile subgraph.
3. OPTIONAL dependencies are used only when explicitly included.
4. FORBIDDEN dependencies must not be included.
5. A dependency's expected output types must be declared by the parent StageSpec.
6. Each stage input type must be supplied by a declared parent or an explicit external input binding.
7. Cycles, hidden dependencies and undeclared type coercion fail closed.
8. Topological ordering is deterministic and lexicographic among simultaneously ready stages; registration and parent-declaration order are non-semantic.
9. Blocked-descendant reporting is graph-derived and does not rewrite the profile.

## Adapter protocol

A registered stage adapter exposes preflight, estimate, execute, resume and verify hooks. Registration only proves a callable boundary exists; it grants no owner-programme authority. Adapter wrappers may add execution-envelope metadata but must not mutate scientific payload fields. Source-stage authority, chronology, first-valid semantics, clocks, sides, packs, selectors and scientific result statuses remain owner-programme responsibilities.

## Extension rule

A future stage may be added by a versioned StageSpec, adapter and profile registration without scheduler source-code changes, provided its dependency and type contracts validate. Registration is not scientific or activation authority.

## Failure posture

Planner and adapter violations use explicit IROF reason codes and fail closed. No synthetic substitution, profile degradation, dependency inference from payload values or silent wrapper repair is allowed.

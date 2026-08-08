# OccurrenceContext Contract v0.1

Status: FROZEN_ENGINEERING_CONTRACT under `OVC-OCCURRENCE-CONTEXT-IMPLEMENTATION-PLAN-0.1`.

## Invariant
OccurrenceContext describes the circumstances of an immutable structural occurrence; it never changes what that occurrence historically was.

## Identity
`occurrence_key` is derived only from immutable structural-anchor fields: `anchor_kind`, `anchor_id`, `anchor_schema_id`, and `anchor_logical_hash`. Context values never participate. `occurrence_context_id` identifies one exact contextualisation and binds schema version, context pack, occurrence key, immutable anchor ref, role-map identity, dependency-set hash, registry-binding hash, and context first-valid time.

## Lawful anchors
`C2_OBSERVATION`, `C2E_EPISODE_GENESIS`, `C2E_EPISODE_SNAPSHOT`, `C2E_PHASE_SEGMENT`, `SRI_OCCURRENCE_REPRESENTATION`, `FDI_OCCURRENCE_ASSIGNMENT`. SRI/FDI aliases MUST resolve to an immutable structural anchor. Family IDs, prototypes, semantic labels, outcomes and cohorts are forbidden primary anchors.

## Envelope
The v0.1 envelope carries source/instrument/side lineage, research role, occurrence interval, calendar/session/clock/scale context, typed parent links, optional market-condition context, lawful C2E-relative context, typed MCARB refs, field-role map, dependency refs, first-valid time, availability, reason codes, authority state, lineage, and logical hash.

## Versioning
Context records are immutable. Later evidence or registry versions create successor records; they never overwrite prior records. Schema, context pack, session/calendar registry, role map, market-condition vocabulary and auxiliary-admission versions are independently governed.

## Authority
The base pack is non-structural. `REPRESENTATION_INPUT` is denied. Validation occurrence access, new instrument/market/side/clock/lattice, MCARB scientific activation, C2P, selector/publication and probability/risk/exposure/execution are outside this contract.

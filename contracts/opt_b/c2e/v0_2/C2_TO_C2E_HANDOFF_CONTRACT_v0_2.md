# C2 -> C2E Handoff Contract v0.2

Programme: `OVC-C2E-CAUSAL-EPISODE-CONFORMANCE-v0.2`  
Packet: `C2E2-WP1`  
Authority: inactive, noncanonical build/test only.

## Purpose

Materialise the typed `C2EInputFrame` required by the accepted C2E v0.2 design without reducing revised C2 to a composite state string, reconstructing a fifth QUALITY market-state axis, or importing downstream/future evidence.

## Exact upstream binding

The adapter accepts only `C2AR.INTEGRATED.SHADOW.PACKAGE.v1` at SHA-256 `150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3` with `READ_ONLY_SHADOW_RESEARCH_ONLY` permission, `active=false`, and `canonical=false`. Source release, source manifest, C2 release, C2 contract and source build commit are mandatory per frame namespace.

## Frame families

Identity binds instrument, side, scope, scale, clock, lattice, observation/C2 record, parameter pack, contract and schema IDs. Chronology binds source time, optional candidate onset, first-valid time, evaluation cutoff, continuity segment and predecessor identity. Structural state consists only of LOCATION, MOTION, ORGANISATION and INTERACTION record references plus level, container, RelationSet, transition and run references. Context binds the context-resolution bundle and typed parent/object/axis links. Evidence carries dependency results, availability, technical computability, assurance, consumer eligibility, authority and reason codes. Lineage carries the complete parent-record inventory, artifact hashes and source build commit.

## Invariants

1. Every parent record referenced by a frame is first-valid no later than the frame and evaluation cutoff.
2. One frame binds one exact source/C2 release, instrument, side, scope and scale; no implicit cross-side or cross-release join exists.
3. Continuity is explicit and never repaired or backfilled by C2E.
4. Structural axes are exactly LOCATION, MOTION, ORGANISATION and INTERACTION. QUALITY is not a structural axis.
5. Dependency failure is selective: a missing parent-relative dependency may make only dependent rules not evaluable; it does not globally invalidate unrelated local evidence.
6. FDI/C2G family, cluster, medoid, distance, sensitivity or recurrence data; implicit C2P annotations; C2.5/C3; outcomes/future path; research queues; and retrospective optimal segmentation are prohibited causal inputs.
7. Frame identity is deterministic from birth-available identity and exact source bindings. Later source releases cannot mutate an existing frame namespace.
8. Unknown top-level handoff fields fail closed except an explicitly non-identity `diagnostic_namespace`.

## Non-authority

A conforming frame is an input contract, not an episode, boundary-pack selection, source replay, selector, publication, Validation, family/semantic claim, probability, risk, exposure or execution authorization.

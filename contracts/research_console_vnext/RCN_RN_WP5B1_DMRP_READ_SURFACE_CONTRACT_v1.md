# RCN-RN-WP5B1 DMRP Research Operations Read Surface Contract v1

## Purpose

Expose a bounded fixture-only Research Console projection of DMRP Path 1, Path 2, ResearchCandidateGeneration and cross-mode evidence without constructing, repairing, ranking, merging or promoting research objects.

## Authority

- Packet: `RCN-RN-WP5B1`
- Transport: `GET_ONLY`
- Presentation mode: `FIXTURE_ONLY`
- Evidence status: `NON_EVIDENTIARY`
- Authority effect: `NONE`
- Validation: `LOCKED_UNCONSUMED`
- First new real DMRP Research source: `false`
- Reserved escalation: `RCN-RN-G5-FIRST-NEW-SOURCE[DMRP]`

This contract grants no real-source DMRP Console presentation, candidate freeze, candidate/theory/semantic promotion, Development/Validation consumption, publication, probability, risk, exposure, trading, execution or write authority.

## Source ownership

The console consumes exact synthetic owner fixtures only. DMRP remains authoritative for research-mode semantics and canonical ResearchCandidateGeneration identity. The console MUST NOT infer scientific facts from file names, route presence, implementation state or UI state.

## Required invariants

1. Path 1 and Path 2 provenance remain distinct.
2. Canonical candidate series/generation identity is copied exactly from the bound DMRP fixture.
3. Other owner-native theory/intake identities are not collapsed into candidate identity.
4. `correspondence != independence`; no missing exposure record may be rendered as independence.
5. Negative/divergent/not-evaluable evidence remains visible.
6. No path winner, ranking score, construction action, repair action, identity merge or promotion action exists.
7. All source files are bound by repository-relative path, schema, authority marker and exact Git blob SHA.
8. Missing/moved/conflicting source files fail closed.
9. The endpoint is `GET /api/v1/research/dmrp/snapshot`; frontend route is `/research/dmrp`.
10. Any future first real DMRP presentation requires an exact independent source preflight and, absent existing presentation authority, operator PASS at `RCN-RN-G5-FIRST-NEW-SOURCE[DMRP]`.

## Rollback

Disable/remove the bounded fixture route, component, bindings and fixture resource while preserving source-owner records, packet evidence and Git history. Rollback creates no source or scientific authority change.

# P2CTI Core Boundary Contract v0.1

Programme: `OVC-P2CTI-CONFORMANCE-v0.1`  
Packet: `P2CTII-WP1`  
Authority effect: **NONE**.

## Purpose

P2CTI is an additive Research Operations inventory/control plane over DMRP Path-2 theory-origin objects. It indexes and relates exact owner objects; it does not replace or rewrite `TheoryRecord`, `ResearchProtocol`, `ExperimentRecord`, `ResearchCandidateGeneration`, RCCR, EC1, Research Console or System Atlas.

## Canonical ownership

P2CTI may own only its inventory/control records: series, generations, entries, source-frontier and bootstrap manifests, theory seeds/triage, relation/duplicate evidence, research demand, work/deferral records and visibility decisions. Scientific payload remains owned by the declared source programme. A P2CTI inventory entry MUST carry an exact source reference and MUST NOT copy an owner scientific payload into P2CTI canonical state.

## Non-transitivity

The following are constitutional inequalities:

`CAPTURED != THEORY`  
`THEORY != CANDIDATE`  
`CANDIDATE_PROPOSAL != CANDIDATE_FREEZE`  
`NEED_SUPPORTED != CAPABILITY_ACTIVATION`  
`IMPLEMENTED != OPERATIONAL_RELIANCE`  
`OWNER_AUTHORITY != P2CTI_AUTHORITY`

P2CTI construction, schema validation, hashing, indexing, queryability or technical PASS never grants scientific, candidate, semantic, Validation, publication or exposure authority.

## State separation

Theory lifecycle, evidence state, Path-2 frontier, formalisation state, candidate relation, authority and currentness are orthogonal planes. No adapter may collapse these planes into one convenience status or infer one plane from another.

## Current programme boundary

Before `P2CTII-G-OBSERVABILITY-ACTIVATE`, P2CTI output may be built and used in read-only shadow/advisory assurance only. Durable intake writes remain denied before `P2CTII-G-CONTINUOUS-INTAKE`. Theory semantic freeze, P2-6 candidate formation and candidate-generation freeze remain outside P2CTI.

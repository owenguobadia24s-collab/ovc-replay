# P2CTI Owner Source Adapter Contract v0.1

Programme: `OVC-P2CTI-CONFORMANCE-v0.1`  
Packet: `P2CTII-WP1`  
Authority effect: **NONE**.

## Rule

Every P2CTI projection that describes an owner-controlled fact MUST carry an exact `OwnerSourceReference` identifying owner programme, object type, object identity, semantic generation/version where applicable, repository/source locator, content hash and authority references.

Adapters are reference translators only. They MUST NOT:

- copy owner scientific payload into a P2CTI canonical object;
- synthesize evidence state when no owner assessment exists;
- infer Path-2 stage, candidate relation or authority from naming, recency or file location;
- convert RCCR `NEED_SUPPORTED` into capability activation;
- treat missing DMRP exposure records as independence;
- inherit Path-2 or EC1 real-source authority into P2CTI.

Missing or conflicting owner evidence is represented explicitly and is resolved by the WP2 owner/currentness engine; WP1 adapters do not choose a winner.

## Known owner families

The initial registry supports DMRP Path-2 `TheoryRecord`, `ResearchProtocol`, `ExperimentRecord` and `ResearchCandidateGeneration` references; RCCR coverage/gap/capability-need records; EC1 research objects; and exact authority/exposure/correspondence references. New owner families require a registry amendment and cannot be inferred from arbitrary paths.

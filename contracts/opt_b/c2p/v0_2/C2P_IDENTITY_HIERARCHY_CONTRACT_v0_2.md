# C2P Identity Hierarchy Contract v0.2
Status: FROZEN_INACTIVE_CONFORMANCE / authority_effect=NONE

The constitutional sequence is `Observation -> Candidate -> Tracklet -> ObjectAssertion -> optional StructuralReferent`.
Only `C2PObjectAssertion` is durable identity in the ratified core. Candidate and Tracklet IDs are immutable but non-durable.
`StructuralReferent`, MigrationMap and ReconciliationPack runtime are deferred outside the default programme.
No downstream consumer may promote a Tracklet to canonical referent or rewrite an ObjectAssertion identity.

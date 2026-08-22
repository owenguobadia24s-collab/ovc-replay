# OVC Shared Systems persistence, security and observability contract v0.1

Status: inactive/reference constitution under `SHSI-WP6`; authority effect `NONE`.

Persistence separates logical artifact identity from stored bytes and physical
location. `DurableArtifactDescriptor`, `ExternalArtifactReceipt`,
`EvidenceCommitManifest` and `EvidenceReachabilityManifest` bind exact hashes, sizes,
owners, storage/retention classes, completeness and current reachability. Only an exact
complete verified set is `SEALED`; missing and hash-mismatched evidence remain typed
gaps. This layer creates no central domain store and performs no deletion or compaction.

Security reuses exact DSAI decisions through `DSAISecurityAdapterBinding`; it creates
no credential, permission or authority store. `SecurityRequest` and
`SecurityDecisionRecord` preserve the six independent factors: capability, technical
reachability, permission, authority, scope and runtime policy. Every factor must pass.
Denied protected requests stop before path, locator, hash, existence, count or
timestamp metadata is resolved. `InformationExposureRecord` makes Validation exposure
irreversible provenance; it does not grant Validation authority.

`TelemetryRecord`, `HealthAssertion`, `ServiceHealthSnapshot` and
`ServiceLevelObjective` are operational evidence only. Availability, correctness,
freshness, dependency, capacity, performance, persistence, security, qualification
and queue dimensions remain independent; `UNKNOWN` is not green and no aggregate
authoritative health score exists. Wall-clock observation does not redefine FVT or
effective chronology. Unmeasured SLOs remain `UNBOUND`.

`PilotBaselineMeasurement` and `PilotAcceptanceBudget` retain independent dimensions.
All numeric caps must derive mechanically from pinned evidence through the documented
WP6 procedure. The complete constitutional hard floor is exactly zero and caps cannot
be relaxed during the pilot to obtain PASS. Budget evidence grants no activation,
scientific or operator authority.

Nothing here accesses a protected resource, creates a second security/artifact store,
changes a consumer binding, runs science, consumes Validation, publishes canon/R2, or
grants probability, risk, exposure or execution authority.

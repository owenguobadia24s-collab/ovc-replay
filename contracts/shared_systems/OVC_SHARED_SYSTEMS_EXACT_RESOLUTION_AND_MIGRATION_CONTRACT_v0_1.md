# OVC Shared Systems exact resolution and migration governance contract v0.1

Status: inactive/reference constitution under `SHSI-WP5`; authority effect `NONE`.

Resolution is library-first and exact. A `ResolutionRequest` names an exact service
release, consumer generation, capability, contract, semantic scope, authority,
environment and optional cutoff. Normative `latest` is forbidden. A successful
`ResolutionManifest` binds the exact owner registry, service release, contract,
compatibility evidence, adapter chain, qualification, consumption binding, authority
and environment. Missing, ambiguous, stale, incompatible, unauthorized, quarantined,
owner-conflicting or unmaterialized inputs produce typed fail-closed manifests.

`RegistryDirectory` is a rebuildable, non-authoritative locator over owner registries.
It cannot supply registry contents or override the exact Stage-0 owner binding.
`SharedServiceDescriptor` and the GRT `SharedServiceBinding` must agree on owner.

`SharedExecutionContext` freezes a successful manifest for local execution.
It cannot advance merely because a directory/current projection changes; re-resolution
requires an explicit barrier and a newly successful exact manifest. Service and
consumer current-binding records are restricted to `INACTIVE_REFERENCE` or
`SHADOW_ONLY` in this packet.

Compatibility and adapter registries are closed exact registries. Adapters may apply
only declared mappings and losses from WP2; they cannot invent domain facts or
authority. Incompatible, unknown, historical-only, missing, or ambiguous mappings do
not resolve for normal consumption.

`MigrationInventory` and `NonMigrationDecisionRegistry` are evidence-only governance
projections. Triggered non-migration decisions require review; they do not migrate,
activate, retire or replace a consumer binding.

Nothing in this contract changes a current domain consumer, owner registry, frozen
semantic contract, source/provider/research role, Validation boundary, canon/R2 state,
scientific result, probability/risk/exposure plane, or execution authority.

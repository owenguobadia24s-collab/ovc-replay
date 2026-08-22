# SHSI-WP5 exact registry, resolution and migration-governance materialisation

Status: implemented candidate pending exact-head repository assurance. Authority delta: `NONE`.

This packet adds an inactive, in-process exact resolver. The `RegistryDirectory` is a
non-authoritative locator over exact owner registries and rejects any disagreement with
the Stage-0 owner binding. Requests name exact releases and contracts; normative
`latest` is rejected. Success freezes owner, release, registry, contract,
compatibility, adapter, qualification, consumer binding, authority and environment.

Missing/ambiguous releases, owner conflict, stale qualification, incompatibility,
missing adapters, missing authority, quarantine and absent materialisation are typed
fail-closed outcomes. A successful `SharedExecutionContext` changes only through an
explicit re-resolution barrier.

Migration inventory and non-migration decisions are evidence-only. All service-current
and consumer-binding objects remain `INACTIVE_REFERENCE` or `SHADOW_ONLY`; no current
domain binding is changed.

Rollback: remove the inactive resolver/bindings and rebuild projections from exact
Stage-0 records; preserve qualification and migration/non-migration evidence.

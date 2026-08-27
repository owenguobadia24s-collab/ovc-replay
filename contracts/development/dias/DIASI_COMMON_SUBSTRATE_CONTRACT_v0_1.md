# DIASI common deterministic substrate contract v0.1

This contract governs `DIASI-WP1`. The implementation is owner-local, deterministic, and side-effect free. It creates no scheduler, service, physical writer, liveness authority, proof-substitution authority, or generic governance platform.

## Authority envelope

`ProgrammeAuthorityEnvelope` is closed-world. It binds one programme, plan, packet, gate, exact authority sources, allowed actions, denied actions, write families, reserved boundaries, rollback, and optional expiry. Undeclared actions are denied. Allowed and denied actions may not overlap. Authority does not transit from evidence production, source admission, consumer admission, research role, currentness, or recency.

## Consequence classifier

Every declared effect belongs to `FLOW`, `EVIDENCE`, or `AUTHORITY`. Unknown or absent effects fail closed. An action that contains an authority effect and another plane must be split; evidence may proceed in its own envelope, while the authority consequence remains held for its controlling gate. Classification never grants authority.

## Dependency tokens and test manifests

Dependency tokens use `KIND:value`. Kinds are closed to the vocabulary in `dias.py`; credential tokens carry logical references only. `TestDependencyManifest` binds each test to an assurance class and exact dependency tokens. Unresolved dependencies block.

## Owner-source precedence

Current owner pointers control over referenced owner state, owner receipts, and derivative observations. Within the controlling tier, equal facts coalesce and unequal facts block. Lower-tier recency never overrides an owner fact. Missing facts block.

## Current execution projection

`CurrentExecutionProjection` is a derivative shadow view of resolved owner facts. It has no authority effect, cannot become a writer, and cannot be used as an owner-currentness source. It is rebuildable from the referenced facts.

## Canonical identity registry

Only registered `DIASI-WP*` packet identities and `DIASI-G*` gate identities are accepted. Unknown identities deny. The registry is identity-bearing evidence and not an authority source.

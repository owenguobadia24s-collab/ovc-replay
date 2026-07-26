# C1 Release Lifecycle Contract v0.1

## Status

`FROZEN_AFTER_WP2`

## Scope

This contract defines C1 release, manifest, approval, selector and supersession records. It does not create a release or grant publication or selector authority.

## Identifiers

- Formula registry: `C1.FORMULAS.v0.1`
- C1 release: `OPT-B.C1.<INSTRUMENT>.<ROLE>.<INTERVAL>.v<MAJOR>`
- Manifest: `MANIFEST.C1.<RELEASE-SLUG>.<REVISION>`
- Publication record: `PUB.R2.C1.<RELEASE-SLUG>.<REVISION>`
- Selector: `SELECTOR.OPT-B.C1.<ROLE>`
- Record: `c1:<sha256>`

## Orthogonal states

Lifecycle:

`DRAFT -> CONTRACT_FROZEN -> IMPLEMENTED -> FIXTURE_VERIFIED -> REPLAY_BUILT -> RELEASE_FROZEN -> LOCAL_VERIFIED -> PUBLICATION_APPROVED -> PUBLISHED -> REMOTE_VERIFIED`

Authority:

`NONE | CANDIDATE | SHADOW | ACTIVE_DISCOVERY | ACTIVE_DEVELOPMENT | ACTIVE_VALIDATION | HISTORICAL | SUPERSEDED`

QA:

`NOT_EVALUATED | PASS | WARN | BLOCK | QUARANTINE`

Availability:

`LOCAL_ONLY | REMOTE_PRESENT | REMOTE_VERIFIED | PARTIALLY_AVAILABLE | MISSING`

Compatibility:

`NOT_EVALUATED | EXACT | EXPECTED_DIFFERENCE | UNEXPLAINED_DIFFERENCE | NOT_COMPARABLE`

Publication:

`NOT_ATTEMPTED | APPROVED | PUBLISHED | NEVER_PUBLISHED | ABANDONED_BY_POLICY`

## Release construction conditions

A C1 release may not be frozen until:

1. WP3 fixture trust passes;
2. an exact approved OPT-A v2 parent release and manifest are named;
3. the role, interval, clocks and sides are approved;
4. the complete external record inventory exists;
5. deterministic replay and local verification pass;
6. all blocker checks are closed;
7. an operator decision names the exact inventory and rollback target.

WP2 and WP3 do not satisfy these conditions.

## Manifest law

The C1 manifest binds:

- exact C1 release and manifest identities;
- exact parent OPT-A release and manifest hashes;
- formula-registry and schema hashes;
- source/build commit;
- every external file path, byte size and SHA-256;
- record count by role, clock and side;
- QA packet identity and state;
- no-overwrite canonical remote keys.

Payloads publish first and the manifest publishes last. A remote payload without its manifest is non-authoritative.

## Publication approval

Publication requires a separate exact approval record bound to release ID, manifest ID, manifest SHA-256, source commit, target bucket/prefix, operator decision and rollback note. Approval is single-manifest and non-transferable.

## Selector law

- Initial C1 activation may be `SHADOW` only.
- C2 remains read-disabled until a later exact handoff review.
- Validation cannot be selected or consumed without a separate exact approval.
- Selector updates are atomic and versioned.
- Rollback points to `NONE` or a prior eligible C1 release; historical OPT-A v1 and legacy OPT-B are prohibited targets.

## Supersession

A changed formula, null policy, schema, input profile or parent-release identity creates a new C1 release identity. Supersession preserves the predecessor manifest, selector history and reason. No historical object is overwritten or relabelled.

## Storage boundary

Git stores contracts, schemas, registries, compact manifests, QA packets and decisions. Full C1 streams remain outside Git under the external artifact root and immutable R2 namespace.

## Current authority

WP2 freezes design only. Market replay, release freeze, R2 publication, selector activation, C2 consumption, probability, exposure, trading and execution remain denied.
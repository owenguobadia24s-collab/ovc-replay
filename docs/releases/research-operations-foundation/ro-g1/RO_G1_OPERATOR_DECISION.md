# RO-G1 — Evidence Integrity Operator Decision

## Disposition

`PASS — RO-WP2 AUTHORISED FOR BUILD`

## Exact review baseline

- Repository: `owenguobadia24s-collab/ovc-replay`
- Branch reviewed: `main`
- RO-WP1 merge commit: `8944da84dec4915c7d7748ae5dbb2a9e1d187d28`
- Predecessor gate: `RO-G0 PASS`
- Validation release: `OPT-A.GBPUSD.VALIDATION.2025.v2`
- Validation consumption: `LOCKED_UNCONSUMED`

## Review scope

RO-G1 reviewed the frozen RO-WP1 evidence kernel, including:

- the authority, envelope, cutoff and lifecycle contracts;
- the ten-type JSON Schema bundle and record registries;
- canonical UTF-8 JSON and deterministic record identity;
- freeze verification and append-only supersession;
- explicit artifact availability and reproducibility states;
- synthetic valid, partial, missing, leakage, mutation, locked and censored fixtures;
- executable evidence-integrity tests.

## Findings

The operator review confirms that:

1. a valid record chain can be reconstructed from immutable identities and lineage;
2. model references are optional, so an OPT-A-only observation is lawful;
3. post-cutoff references reject as `POST_CUTOFF_REFERENCE`;
4. Validation metadata is visible while payload access rejects as `VALIDATION_PAYLOAD_ACCESS_DENIED`;
5. frozen-byte mutation rejects as `FROZEN_MUTATION`;
6. duplicate deterministic record IDs reject;
7. missing required artifacts remain visible as `PARTIALLY_AVAILABLE` or `NOT_REPRODUCIBLE`;
8. supersession preserves predecessor bytes and creates a new successor identity;
9. no RO-WP1 object gains market, probability, exposure, execution or agent authority.

## Authority delta

RO-G1 authorises only:

```text
RO-WP2 — Research CLI and artifact catalogue
```

This is build authority, not active-research authority. RO-WP2 may implement governed append-only writes, audit emission and artifact-catalogue operations within the frozen RO-WP1 contracts.

The following remain absent or denied:

- active operator research authority;
- a deployed durable write service;
- QA-runner, read-model or console authority;
- Validation payload access;
- provider access or R2 mutation;
- OPT-A or OPT-B mutation;
- selector or threshold mutation;
- probability, exposure, trading, execution or agent authority.

## Rollback

Rollback removes RO-WP2 build authority while preserving all RO-WP1 contracts, schemas, fixtures, tests and historical decision evidence.

## Next bounded packet

`RO-WP2 — Research CLI and artifact catalogue`

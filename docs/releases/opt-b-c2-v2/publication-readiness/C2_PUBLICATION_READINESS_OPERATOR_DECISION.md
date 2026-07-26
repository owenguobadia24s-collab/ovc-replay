# C2 publication readiness and operator approval

## Decision

**PASS — approve immutable R2 publication of the exact frozen C2 Discovery and Development candidates only.**

This decision authorises the next bounded operation to upload the two exact candidate release roots using payload-first, manifest-last publication and then stream every remote byte for size and SHA-256 verification.

It does **not** publish either release in this review, does not create or mutate a C2 selector, and does not activate C2.

## Approved release identities

| Role | Release | Manifest | Manifest SHA-256 | Candidate artifact |
|---|---|---|---|---:|
| Discovery | `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1` | `MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1.r1` | `c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33` | `8634803012` |
| Development | `OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1` | `MANIFEST.C2.OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v1.r1` | `8a37e931ac003e88c8e1b3c4f8a1849e947f86f47e982e00ca4723e53fd9586e` | `8634803579` |

Candidate tree SHA-256: `f15ad152405708bca09e0255af6de69a4a54051e6f0f9e2128cd0c2944bf60fd`.

## Review execution

- Workflow: `C2 publication readiness and operator approval`
- Workflow run: `30213663356`
- Verified branch commit: `0a896b8ce5f4fbf3caddb16e20702f9d7f93ae0f`
- Result artifact: `8635181040`
- Result artifact digest: `sha256:cc4f1a0997b56867a7a5cf8a03be3c326d275870d195039555c2c5eb0b45d27d`
- Artifact expiry: `2026-10-24T17:57:14Z`

## Evidence reviewed

The review passed all of the following:

- exact GitHub artifact ID, name, digest, source-run and source-commit binding;
- C2-G5 candidate tree and gate-packet identity;
- manifest self-hashes and complete manifest inventories;
- full-byte verification of 36 manifest-bound files totalling 872,867,602 bytes;
- 404,434 state records and 323,910 transition records;
- exact OPT-A and C1 parent release and manifest binding;
- current C2 contract, schema, registry and parameter-pack hash binding;
- zero blocking, open or unresolved QA issues;
- absence of both exact canonical R2 namespaces before publication;
- full canonical repository test-suite success.

## Approved publication method

The next operation must:

1. download artifact `8634803012` and verify its recorded digest and internal manifest;
2. download artifact `8634803579` and verify its recorded digest and internal manifest;
3. recheck both exact remote prefixes for collision immediately before writing;
4. upload every manifest-bound payload object under its exact immutable prefix;
5. upload `manifest.json` last as the completion marker;
6. stream every remote object back and verify size and SHA-256;
7. emit a compact remote-verification receipt and publication record into Git;
8. stop before selector creation, selector mutation, B-STATE retirement or C2 activation.

Any collision, partial upload, hash mismatch, absent approval binding or failed readback is a blocking result. Partial objects remain non-authoritative without the manifest completion marker and must not be selected.

## Retained authority

- C2 publication execution: `NOT_YET_EXECUTED`
- C2 selector: `NONE`
- C2 activation: `NONE`
- Direct `ACTIVE_DISCOVERY`: `DENIED_PENDING_REMOTE_VERIFICATION_AND_SEPARATE_SELECTOR_RETIREMENT_TRANSACTION`
- Validation consumption: `LOCKED_UNCONSUMED`
- C2E, C2.5 and C3: `DEFERRED`
- New OPT-C and OPT-D authority: `NONE`
- Probability, exposure, trading and execution: `NONE`

## Next boundary

`C2_R2_PUBLICATION_AND_FULL_REMOTE_VERIFICATION_EXACT_RELEASES_ONLY`

After remote verification, a separate operator-reviewed selector, legacy-retirement and rollback-to-C1-only transaction is required before C2 may become `ACTIVE_DISCOVERY`.

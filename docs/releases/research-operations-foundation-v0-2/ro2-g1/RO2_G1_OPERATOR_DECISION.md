# RO2-G1 — deterministic workspace-index acceptance

## Decision

`PASS — LOCAL REPLACEABLE DERIVED INDEX ONLY`

RO2-WP1 is accepted for bounded local operation. The accepted implementation deterministically builds role-workspace, observation and observation-family indexes for the approved OPT-A Discovery and Development releases. It exposes Validation aggregate metadata only and denies Validation content before path, object or row resolution.

The gate is reconciled to integrated `main` commit `e2935f0c607aa25c565da59c08e15263176213d6`, which separately approved exact C2 R2 publication readiness without executing a remote write or granting selector or activation authority.

## Verification basis

- RO2-G0 parent design validator: `PASS`
- focused RO2-WP1 tests: `5 PASS`
- independent fixture builds: identical logical index SHA-256
- logical fixture index: `dcb88c5f9c9fc0d4dbd12ac6a293607a1067fc11cfd9f19f72c4f497bd0da697`
- full repository suite: `70 PASS`
- dedicated acceptance run: `30214437661`
- canonical tests run: `30214437602`
- tested implementation commit: `474534310b9dec679aa9e7c94fb3556856a24901`

## Authority granted

The following capability is accepted:

- local deterministic indexing of approved Discovery and Development release metadata and observation rows;
- local deterministic observation-family grouping;
- stable logical index identity independent of source ordering;
- read-only Validation aggregate metadata projection;
- fail-closed rejection of unknown roles, conflicting duplicate identities and Validation content-resolution attempts.

The index is replaceable and never outranks its source release, manifest or record.

## Authority not granted or modified

RO2-G1 does not grant or modify:

- Validation row, timestamp, path, key, object or content access;
- market classification or model authority;
- C2 R2 publication execution, selector or activation authority;
- quality, bar-lineage, replay or release-difference implementation;
- Git, R2, release, selector or threshold writes by RO2;
- probability, exposure, trading or execution authority.

The separately approved C2 authority remains `AUTHORISED_EXACT_RELEASES_ONLY / NOT_YET_EXECUTED`. C2 selector and activation remain `NONE`. Validation remains `LOCKED_UNCONSUMED`.

## Next boundary

RO2-WP2 is authorised for a separately instructed build. No RO2-WP2 implementation begins through this decision alone.

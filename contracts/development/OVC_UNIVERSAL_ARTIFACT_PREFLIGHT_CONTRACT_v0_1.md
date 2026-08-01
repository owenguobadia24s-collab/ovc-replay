# OVC Universal Artifact Preflight Contract v0.1

## Authority

`FAIL_CLOSED_EXECUTION_GUARD` only. Preflight is read-only and may issue deterministic PASS, WARN, BLOCK, QUARANTINE or NOT_EVALUABLE receipts. It does not run the guarded computation, create directories, copy files, modify repository state, publish, mutate selectors, write R2, consume Validation or grant repository-bot authority.

## Inputs

- one approved strict `ovc-artifact-profile/v1` profile;
- exact artifact references bound by logical name, relative path, identity policy, size and SHA-256;
- an operator-supplied input root not persisted by the tool;
- zero or more destination checks under a separately supplied destination root.

All required profile inputs must have exactly one declared reference. Undeclared references, duplicate logical names, path or identity-policy mismatches and unsafe paths block.

## Checks

1. Reserved authority remains denied in the loaded profile.
2. Exact source file exists, is a regular non-symlink file, has the declared byte length and SHA-256.
3. JSON artifacts with a declared schema ID contain the same top-level `schema` marker.
4. Destination policy is either `ABSENT` or `ABSENT_OR_EMPTY`.
5. Existing files, non-empty directories, symlinks or unsafe destinations block.
6. Results are deterministically ordered and hashed without local root paths, timestamps, machine names or duration.

## Status rules

`QUARANTINE > BLOCK > NOT_EVALUABLE > WARN > PASS`.

A missing required reference, missing file, mismatched bytes, mismatched schema, undeclared input or destination collision is BLOCK. Optional missing inputs may WARN. Unknown or ambiguous conditions must not silently PASS.

## No-write guarantee

The preflight API and CLI inspect only. Tests compare directory snapshots before and after execution. Receipt output is emitted to stdout or returned to the caller; persisting it is the responsibility of a separately governed packet workflow.

## Timing target

Compact-profile median under 30 seconds and inventory-profile completion under 90 seconds. DA-WP2 fixtures are expected to complete far below these limits; future programme profiles must record measured timing without placing elapsed time inside logical identity.

## Rollback

Revert the bounded DA-WP2 merge or stop invoking preflight profiles. Preserve all prior receipts and incidents. Programme-specific validators remain valid and no historical result is rewritten.

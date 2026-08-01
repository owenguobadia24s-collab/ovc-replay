# OVC Universal Artifact Preflight — Operator Guide v0.1

## Purpose

Use the shared preflight before an approved packet performs expensive or irreversible local computation. The command validates exact compact inputs and destination collision state. It never runs the packet, creates directories, persists receipts, publishes, changes selectors or writes the repository.

## Inputs

1. A strict JSON artifact profile using `ovc-artifact-profile/v1`.
2. A JSON array of exact artifact references.
3. An existing input root containing only the referenced relative paths.
4. An existing destination root when destination checks are requested.
5. Optional destination checks using `ABSENT` or `ABSENT_OR_EMPTY`.

Machine-specific roots are command arguments and must not be committed.

## Example

```powershell
$env:PYTHONPATH = "src"
python scripts/development/ovc_preflight.py `
  --profile fixtures/development/preflight/profile_pass_v0_1.json `
  --refs fixtures/development/preflight/refs_pass_v0_1.json `
  --input-root fixtures/development/preflight `
  --destination-root C:\path\to\approved\external-root `
  --destinations fixtures/development/preflight/destinations_pass_v0_1.json
```

Exit codes:

- `0`: PASS;
- `1`: a valid request produced WARN, BLOCK, QUARANTINE or NOT_EVALUABLE;
- `2`: the request itself was invalid or unreadable.

## Stop conditions

Do not begin the guarded computation when:

- the profile is missing, ambiguous or over-authorised;
- a required reference is absent;
- bytes, size, schema marker, path or identity policy do not match;
- a destination exists contrary to policy;
- a root or target is a symlink or escapes the supplied root;
- the receipt is anything other than PASS.

A failed preflight is evidence of a blocked packet, not permission to repair or overwrite inputs. Correct the source packet or profile under its own authority, rerun preflight, and preserve any recorded incident.

## Receipt handling

The command prints canonical compact JSON. Redirecting or committing that output is a separate packet action. Preflight itself records no timestamps, machine names, absolute paths or elapsed duration in logical identity.

## Rollback

Stop invoking the shared preflight or revert its bounded merge through a new commit. Existing programme-specific validators and prior receipts remain valid.

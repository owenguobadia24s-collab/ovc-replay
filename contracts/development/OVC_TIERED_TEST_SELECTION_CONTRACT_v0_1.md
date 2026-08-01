# OVC Tiered Test Selection Contract v0.1

## Authority

`DETERMINISTIC_TEST_PROFILE_SELECTION` only. The selector reads a frozen changed-file inventory and an approved registry, then emits a compact deterministic test manifest. It does not modify source files, weaken or replace stable-head assurance, merge a pull request, write directly to `main`, rerun market computation, publish, mutate selectors, consume Validation or grant repository-bot authority.

## Profiles

| Profile | Purpose | Minimum effect |
|---|---|---|
| `FAST` | Immediate feedback for bounded documentation or low-risk tooling changes. | Run the registered focused checks. |
| `PACKET` | Packet-level contracts, implementation, schemas, fixtures, tests and court records. | Run focused packet tests and retained authority checks. |
| `FINAL_HEAD` | Unknown paths, shared CLI/workflow changes, explicit final-head stage or escalated impact. | Run the complete repository suite. |
| `GATE_REPLAY` | Reproduce a named gate from its frozen command. | Additional evidence only; never substitutes for `FINAL_HEAD`. |

Profile order is `FAST < PACKET < FINAL_HEAD`. `GATE_REPLAY` is orthogonal and always records `final_assurance_required=true`.

## Selection rules

1. Changed paths are normalized repository-relative paths, deduplicated and sorted.
2. Each path is compared against versioned registry rules using deterministic glob matching and explicit integer priority.
3. The highest-priority matching rule owns the path. Multiple highest-priority rules with conflicting owner, profile, commands or retained checks are ambiguous and BLOCK.
4. The selected ordinary profile is the maximum minimum profile across all resolved paths.
5. An unknown path escalates to `FINAL_HEAD`; it is never skipped.
6. An empty changed-file inventory is `NOT_EVALUABLE` and BLOCKS selection.
7. An explicit `FINAL_HEAD` stage overrides any lower selected profile.
8. `GATE_REPLAY` requires a gate ID and frozen command, and records that gate replay substitution is `PROHIBITED`.

## Manifest identity

Logical identity includes the registry ID/hash, normalized changed paths, selected profile, matched rules, unknown paths, commands, retained checks, blockers and assurance requirements. It excludes timestamps, runner names, absolute paths, queue duration and machine-specific values.

## Final assurance

Every manifest must state:

- `final_assurance_required: true`;
- `final_assurance_profile: FINAL_HEAD`;
- `gate_replay_substitution: PROHIBITED`;
- `local_success_substitutes_remote_required_check: false`.

A FAST, PACKET or GATE_REPLAY PASS does not authorise merge. The stable final PR head and any head rebased onto a changed base still require the repository's complete final assurance.

## Failure behaviour

Unsafe changed paths, invalid registry fields, unknown profiles, duplicate rule IDs/patterns/priorities within the same pattern, ambiguous highest-priority matches, missing gate replay data or an empty inventory fail closed. The selector performs no silent repair and does not remove existing tests.

## Rollback

Stop invoking the selector or revert the bounded DA-WP3 merge through a new non-destructive commit. Preserve generated selection manifests for audit. Existing workflows and the complete repository suite remain authoritative.

# OVC Development Acceleration v0.2 CI Admission Baseline Contract v0.2

## Identity

- **programme:** `OVC-DEV-ACCEL-v0.2`
- **packet:** `DA2-00`
- **gate:** `DA2-G0`
- **contract:** `OVC-DA2-CI-ADMISSION-BASELINE.v0.2`
- **authority:** read-only GitHub workflow/check evidence intake and deterministic compact repository evidence
- **workflow mutation:** denied
- **ruleset mutation:** denied

## Purpose

Produce a deterministic account of every pull-request workflow run associated with the two frozen Development Acceleration subjects before any workflow trigger or required context is changed.

## Frozen subjects

1. PR 218 candidate `0f0bda757e62120f2a570de6b3c000e9786445c5`.
2. PR 222 candidate `a1d027ffdf891e666f8a87363ce193684335347f`.

## Raw evidence

The exact raw GitHub REST capture remains outside Git as `DA2_G0_RAW_GITHUB_EVIDENCE.zip`.

Acceptance requires:

- a byte-complete SHA-256 manifest;
- exact workflow run paths, events, conclusions, `created_at`, `run_started_at`, and `updated_at`;
- exact job identifiers, outcomes, `started_at`, and `completed_at`;
- check-suite and check-run GitHub App identities for required contexts;
- no secrets, authorization headers, tokens, or private keys.

The repository stores only the compact baseline and a checksum-addressed Google Drive reference.

## Classification

Every workflow run is classified exactly once as:

- `REQUIRED`;
- `RELEVANT_OPTIONAL`;
- `EXPECTED_SKIPPED`;
- `UNRELATED`; or
- `BLOCKING_SOURCE_MISMATCH`.

The classification registry is frozen with the packet.

## Timing

Run queue and execution durations are calculated only from exact REST timestamps:

- queue = `run_started_at - created_at`;
- execution = `updated_at - run_started_at`.

Negative run durations block the packet.

GitHub may return a skipped job with `completed_at` earlier than `started_at`. For a job whose conclusion is exactly `skipped`, this inversion is preserved as `NOT_EVALUABLE_SKIPPED_INVERTED_API_TIMESTAMPS`; its duration is `null`, the raw timestamps remain unchanged, and no estimate is used. The same inversion for a non-skipped job blocks the packet.

## Required-check source identity

Both ruleset-required contexts must resolve to the accepted GitHub Actions application:

- app ID `15368`;
- app slug `github-actions`.

The check-suite identity and at least one associated check-run identity must both match. A context-name match without accepted source identity blocks.

## Determinism

Canonical logical hashing uses UTF-8 JSON with sorted keys, compact separators and no ASCII coercion. Reprocessing identical ZIP bytes and the same classification registry must reproduce the same logical SHA-256.

## Capacity

- local runtime: maximum 30 minutes;
- CI runtime: maximum 30 minutes;
- compact repository evidence: maximum 1 MiB;
- external raw evidence: maximum 10 MiB.

Capacity excess blocks and preserves partial checksum-addressed evidence.

## Acceptance

DA2-00 passes only when:

1. all 91 runs are accounted exactly once;
2. run paths, events, outcomes and exact run timestamps are complete;
3. job evidence is complete and any skipped-job inversion is explicitly non-evaluable without estimates;
4. the required contexts resolve to the accepted GitHub Actions identity;
5. unrelated fan-out and duplicate complete-suite execution are enumerated;
6. the ZIP manifest and credential scan pass;
7. deterministic rerun reproduces the same logical SHA-256;
8. focused and canonical final-head checks pass;
9. QA recommends `PASS` with no unresolved blocker.

## Failure and rollback

Do not infer absent values or weaken tests. Missing evidence, source mismatch, non-skipped negative duration, manifest mismatch, credential-like material, capacity excess, or non-reproducible output blocks the packet.

Rollback is non-destructive supersession. Preserve the raw ZIP, hashes, baseline, QA, decisions, incident record and prior blocked PR.

# OVC Development Acceleration v0.2 CI Admission Baseline Contract v0.1

## Purpose

Produce a deterministic, read-only account of every pull-request workflow run associated with the two DA2-G0 frozen subjects before any workflow trigger or ruleset is changed.

## Authority

This contract authorises read-only GitHub metadata intake, deterministic classification, compact repository evidence, tests, QA and a later trigger-narrowing proposal. It does not authorise workflow, ruleset, required-context, test, application, provider, R2, publication, selector, semantic, threshold, model, market, Validation, probability, risk, exposure or execution changes.

## Frozen subjects

- PR 218 candidate `0f0bda757e62120f2a570de6b3c000e9786445c5`.
- PR 222 candidate `a1d027ffdf891e666f8a87363ce193684335347f`.

## Required raw evidence

For every workflow run, preserve the unmodified GitHub REST run object and job list. Required fields are:

- run `id`, `workflow_id`, `name`, `event`, `path`, `status`, `conclusion`, `created_at`, `run_started_at`, and `updated_at`;
- job `id`, `name`, `status`, `conclusion`, `started_at`, and `completed_at`;
- required-context check-suite and check-run app identities;
- source commit and pull-request identity.

Raw evidence must be checksum-addressed. Tokens, authorization headers and secrets must not be stored.

## Classification

Each run is classified exactly once as `REQUIRED`, `RELEVANT_OPTIONAL`, `UNRELATED`, `EXPECTED_SKIPPED`, or `BLOCKING_SOURCE_MISMATCH`.

## Timing

Queue and execution durations must be calculated only from exact API timestamps. Job-log timestamps may corroborate required checks but may not substitute for missing run or job API fields. Estimated timing is prohibited.

## Determinism

Canonical JSON uses sorted keys and compact separators for logical hashing. Reprocessing identical raw bytes and the same classification registry must reproduce the same logical SHA-256.

## Acceptance

DA2-00 passes only when:

1. every run for both frozen subjects is accounted exactly once;
2. workflow paths, events and job-level outcomes are complete;
3. required contexts and accepted GitHub App source identities are reproducible;
4. queue and execution durations are reported without estimates;
5. unrelated runs and duplicate full-suite executions are enumerated;
6. the proposed DA2-WP1 diff changes no test or application semantics;
7. focused and canonical repository assurance pass;
8. QA recommends PASS with no unresolved blocker.

## Failure behaviour

Missing API timestamps, workflow paths or app identities produce `BLOCKED_MISSING_EXACT_RAW_RUN_TIMING_AND_SOURCE_IDENTITY`. Preserve partial evidence and request only the missing checksum-addressed raw REST objects. Do not weaken this contract or infer absent values.

## Capacity

- Local runtime: 30 minutes.
- CI runtime: 30 minutes.
- Repository evidence: 1 MiB.
- External raw evidence: 10 MiB.

Capacity excess blocks and preserves partial checksum-addressed evidence.

## Rollback

Supersede through a new immutable baseline version. Preserve raw evidence, hashes, classifications, QA and decisions. No workflow or ruleset mutation exists to revert.

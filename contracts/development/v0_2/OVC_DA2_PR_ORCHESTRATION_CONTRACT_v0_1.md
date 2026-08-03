# OVC Development Acceleration v0.2 PR Orchestration Contract v0.1

## Identity

- **programme:** `OVC-DEV-ACCEL-v0.2`
- **packet:** `DA2-WP1`
- **gate:** `DA2-G1`
- **operator decision:** `DA2-G1.OPERATOR.PASS.20260803T100600+0100`
- **baseline main:** `595dbcfeb951e1c1ab2570debd671b91ec5ec07b`

## Purpose

Replace broad pull-request workflow fan-out with one deterministic orchestration path. The generic `tests` workflow supplies the sole complete repository suite for each pull-request head. The `OVC tiered test selection shadow` workflow selects `FAST`, `PACKET`, or `FINAL_HEAD`, performs focused assurance only, retains the legacy compatibility context during migration, and emits the target `OVC merge readiness` evaluator.

## Admission rules

Only `.github/workflows/tests.yml` and `.github/workflows/ovc-tiered-tests.yml` may listen to `pull_request`.

Completed historical packet and gate workflows are `RETIRED_NON_AUTHORITATIVE_MANUAL_VERIFICATION`. Their exact prior definitions remain retrievable from `595dbcfeb951e1c1ab2570debd671b91ec5ec07b`. The three branch-operated OPT-A workflows retain their prior push/manual jobs but no longer listen to arbitrary pull requests.

Every active workflow has a deterministic concurrency group with `cancel-in-progress: true`.

## Assurance

- `tests` runs the complete repository suite once on Python 3.11.
- `FAST` and `PACKET` remain focused.
- `FINAL_HEAD` in the orchestrator validates focused authority/development boundaries but does not rerun the complete suite.
- `OVC merge readiness` evaluates the canonical `tests` result once on the exact head.
- CI run IDs and merge evidence are recorded after testing through control/receipt records, not committed to the tested candidate.

## Required-context migration

The migration PR must pass the current contexts `tests` and `OVC tiered test selection shadow` from GitHub Actions app ID `15368`. After merge, ruleset `20229411` is to require only `OVC merge readiness`, after exact source-provenance verification. If the ruleset cannot be updated reproducibly, the programme blocks with the workflow migration preserved and the old contexts retained.

## Authority boundaries

This packet changes workflow admission, cancellation, runtime alignment, evaluator emission, and the exact required-context migration plan only. It does not change test assertions, application semantics, provider/R2/publication, selectors, formulas, thresholds, models, Validation, markets, probability, risk, exposure, execution, secrets, dependencies, or agent write authority.

## Rollback

Restore exact workflow definitions from `595dbcfeb951e1c1ab2570debd671b91ec5ec07b` and restore the prior ruleset snapshot through new non-destructive commits. Preserve all decisions, evidence, runs, branches, and merge receipts.

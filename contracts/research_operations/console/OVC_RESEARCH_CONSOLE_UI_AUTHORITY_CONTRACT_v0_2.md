# OVC Research Console v0.2 UI Authority Contract

Document ID: OVC-RESEARCH-CONSOLE-UI-AUTHORITY-CONTRACT.v0.2
Status: FROZEN_BY_RC_00_PENDING_RC_G0_REVIEW
Baseline commit: 4cc23b0f746feaa3fc91d1b6a956a0d4961a88dc
Branch: build/research-console-v0-2-preflight-rc00-current

## Purpose
Freeze the authority, route, control, source and fallback boundaries before visual implementation.

## Authority boundary
The console is a local, replaceable, derived read surface. It may inspect approved records through the deterministic typed read model. It may not mutate repository files, releases, selectors, thresholds, classifications, probability, exposure, execution, agents or deployment state.

| Field | Value |
|---|---|
| mode | READ_ONLY |
| repository_mutation | NONE |
| selector_mutation | NONE |
| threshold_mutation | NONE |
| market_classification | NONE |
| probability | NONE |
| exposure | NONE |
| execution | NONE |
| agent | NONE |
| deployment | LOCAL_ONLY |

## Source and health rules
Every displayed claim, summary, status or count must resolve to immutable source references. Presentation projections never outrank their sources. ALL_CLEAR or PASS requires explicit current PASS or documented NOT_APPLICABLE results for every required domain; no signals, missing inputs or stale indexes are not PASS.

## Route, action and empty-state rules
Every route and visible action must be registered. Unregistered actions are prohibited. Deferred controls are omitted or disabled with an authority explanation. Empty surfaces must use the frozen empty-state registry and state reason, consequence and next valid action.

## Runtime rule
The launcher requires the exact represented commit, validates the read model before launch, fails closed on blockers, binds to 127.0.0.1 and persistently shows the represented commit and read-model hash.

## Change control
Changing route authority, action authority, status meaning, health truth, source allowlists, local binding or deferred-write treatment requires a new contract version and fresh gate review.

## Exit
RC-00 is complete when this contract, the five registries, preflight packet, implementation summary and verification test are committed atomically. RC-G0 remains pending operator review and canonical test evidence.

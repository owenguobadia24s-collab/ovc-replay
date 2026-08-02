# MTA-G0 required-check source observation

- Observation ID: `MTA-G0-OBS-REQUIRED-CHECK-SOURCE-20260802T191100Z`
- Recorded at: `2026-08-02T19:11:00Z`
- Recorded from: operator-provided GitHub ruleset UI evidence
- Repository: `owenguobadia24s-collab/ovc-replay`
- Ruleset: `OVC main protection`

## Observed configuration

The required status-check entries displayed by GitHub are:

1. `tests` — source binding displayed as `Any source`
2. `OVC tiered test selection shadow` — source binding displayed as `Any source`

This observation rules out a required GitHub App/source identity pinned in the visible ruleset configuration. It does not alter, remove or weaken either required check.

## Bounded continuation action

Create this documentation-only branch commit to produce a fresh pull-request `synchronize` event. The exact required checks must run successfully on the resulting current PR head/merge candidate before any squash-merge attempt.

## Authority and rollback

No market, selector, threshold, release, provider, R2, Validation, probability, risk, exposure, execution, agent-write, direct-main, force-push or history-rewrite authority is created. Rollback is non-destructive supersession of this observation if later GitHub evidence contradicts it.

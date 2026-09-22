# OVC Population Allocation & Exposure Register Contract v0.1

Status: ACTIVE FOUNDATION / APPEND-ONLY METADATA GOVERNANCE. Authority effect: NONE.

## Purpose

Provide one central, programme-agnostic court record for OVC market populations, clock views, allocation intent and irreversible research exposure. The register prevents one programme from silently treating a population as untouched after another programme has inspected or used it.

## Identity

1. Population identity is instrument × chronological partition under one source-bank generation.
2. 15M and native 120M counterparts for the same instrument/partition are dependent clock views of one `evidence_group_id`, not independent replications.
3. Archive files and source chunks are provenance surfaces, not automatically independent populations.
4. Changed source bytes require a new source/population generation; exposure history is never reset by renaming or repacking.

## Exposure events

Every decision-bearing interaction appends one event. Event kinds are `METADATA_ONLY`, `PAYLOAD_READ`, `DERIVED_ANALYSIS`, `RESULT_REVEAL`, and `OUTCOME_JOIN`.

Each event binds population, programme, study, research role, event kind and time; clock, protocol, candidate generation and detail references are added when applicable. Events are append-only. Correction is by successor record, never deletion or rewrite.

## Role rules

- Discovery is indefinitely reusable, with prior exposure disclosed.
- Development is preflight-only here. Any substantive prior exposure requires reconciliation; absence of an event never creates Development authority.
- Validation remains locked until separate explicit operator/owner Validation authority exists and exposure reconciliation passes. This register never unlocks Validation.
- One protected population may serve several independently frozen studies in one coordinated exposure batch, but shared observations remain one population evidence source and must not be counted as independent replications.

## Cross-clock and cross-programme dependence

Exposure on any clock view is attached to the underlying evidence group. A narrower clock-specific independence claim requires a separately frozen protocol; the register defaults to conservative same-group dependence.

## Initial seed

The v0.1 seed binds the current Drive `Populations` folder (`1x1Wu8iA-P9UawvSCttOgsoGF2AwjUGHE`) as 32 instrument×partition populations and 64 paired clock views across EURUSD, GBPUSD, EURJPY, USDJPY, AUDUSD, XAUUSD, ES1! and BTCUSD.

Historical bank labels (`P1_DISCOVERY_DEVELOPMENT`, `P2_CONFIRMATION`, `P3_REPLICATION`, `P4_STRATEGIC_RESERVE`) are descriptive provenance only and do not prove current eligibility. All initial exposure states are `UNKNOWN_PENDING_RECONCILIATION`.

## Non-grants

No ACTIVE_DISCOVERY, ACTIVE_DEVELOPMENT, ACTIVE_VALIDATION, Validation consumption, provider intake, new instrument/market/clock activation, selector/model/family/theory/semantic promotion, publication, probability, risk, exposure, trading, execution or agent-write authority.

## Rollback

Forward-revert or supersede implementation while preserving every population binding and exposure event. Never delete exposure history to restore apparent freshness.

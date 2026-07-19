# OVC OPT-A to OPT-B Handoff

## Current state

| Boundary | State | Authority |
|---|---|---|
| OPT-A GBP/USD 2026 H1 | `SEALED_RESEARCH_AUTHORITY` | Canonical research input |
| OPT-B deterministic term contracts | `DRAFT_FOR_REPLAY_VALIDATION` | Not active |
| OPT-B reference-level registry | `BUILT_FOR_REPLAY_VALIDATION_NOT_ACTIVE` | Deterministic input registry |
| OPT-C outcomes | Not started for the level-dependent terms | None |
| Execution | Unauthorized | None |

## Binding input

- OPT-A seal: `OPT-A.GBPUSD.2026H1.v1`
- OPT-A seal hash: `0927f7a2b078d670370eb9ec26718f3e2ff0d97708df1f785a9333264415ef99`
- Registry version: `B-REF-0.1`
- Combined registry hash: `7aa84f4bc774a86cae66992fc753b34e7f35b8576a19e7e84164c1fb9cb5949f`

## What is now possible

The registry supplies lawful, pre-existing reference levels for:

- `REFERENCE_LEVEL_BREACH_AND_RESPONSE` (`SWEEP` alias);
- `RECLAIM`;
- `ACCEPTANCE`;
- `REJECTION`.

Each candidate must be evaluated separately against every eligible level. The engine may not choose an unrecorded “best” level.

## Required next gate

Run the first complete level-dependent historical replay against the sealed 15M and 2H releases. The replay must retain failed, pending, ambiguous and confirmed records, report multiplicity, and prove that no result joins to a level before its `first_valid_time`.

`TRANSITION` remains downstream of the resolved state stream and is not unlocked merely by constructing levels.

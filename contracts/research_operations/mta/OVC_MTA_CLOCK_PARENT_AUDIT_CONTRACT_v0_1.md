# OVC MTA 2H Clock and Parent-Context Audit Contract v0.1

**Programme:** `OVC-MTA-v0.2`  
**Packet:** `MTA-WP4`  
**Gate:** `MTA-G4`  
**Authority:** deterministic audit only; no clock, continuity, formula, threshold, selector, release, Validation or downstream activation authority.

## Purpose

Audit how the frozen June replay maps intervals to the twelve `2H_A_L` UTC blocks and how first-valid 2H parent context reaches each 15M with-parent state. The audit measures mapping, event refresh and clearing, parent age, temporal boundary distance, and reset causes without altering the current implementation.

## Frozen clock mapping

`2H_A_L` is a UTC-day-aligned aggregation of twelve consecutive two-hour buckets. A through L map to interval starts 00:00, 02:00, ..., 22:00 UTC. A 15M record is assigned to the A-L block containing its interval start. This audit records the mapping; it does not approve clock replacement.

## Parent-resolution rule

For each side independently:

1. Every 2H bar end is a parent event.
2. A complete 2H bar refreshes the resolver to the exact C2 level snapshot first-valid at that bar end; the snapshot may be empty during structural warm-up.
3. An incomplete 2H bar clears the active parent level set.
4. A 15M state consumes only the latest event whose event time is less than or equal to its local first-valid time.
5. No forward fill, interpolation, bridging, repair or future-parent use is permitted.

Parent age is measured only for a non-empty resolved level set. Boundary distance is temporal: seconds from the local close to the current two-hour block start, end and nearest boundary.

## Reset causes

Every 15M scope reset must classify exactly once as `SOURCE_PARTITION_START`, `SCHEDULED_WEEKEND_CLOSURE`, `PROVIDER_GAP` or `UNKNOWN`. Provider absence remains explicit and paired across BID/ASK. Unknown resets are blocking.

## Acceptance

MTA-G4 passes only when:

- all A-L mappings are on the fixed UTC grid;
- all 294 two-hour events per side and all 2,231 15M parent resolutions per side are accounted;
- no parent event is consumed before first-valid time;
- incomplete parent buckets clear context and are never bridged;
- BID/ASK interval membership and reset classifications match;
- all reset causes are resolved with zero unknowns;
- compact evidence binds the exact external artifact and frozen inputs;
- focused, retained and complete tests pass;
- QA recommends `PASS_WITH_MATERIAL_FINDINGS`;
- no reserved authority delta occurs.

## Capacity and rollback

The external ledger is below the four-hour/10GB packet limits. Rollback is non-destructive supersession by a new checksum-bound audit version. Source evidence, negative findings and decisions remain preserved.

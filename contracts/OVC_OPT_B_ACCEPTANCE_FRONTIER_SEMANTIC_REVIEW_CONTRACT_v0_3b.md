# OVC OPT-B Acceptance Frontier Semantic Review Contract v0.3b

**Contract ID:** `B-STATE-0.3b-REVIEW`  
**Parent representation authority:** `B-STATE-0.3a-REPRESENTATION-ONLY`  
**Status:** `CONTROLLED SEMANTIC REVIEW — NOT RATIFIED`

## Review variants

All variants read the same lawful one-bar acceptance confirmations:

1. `RAW_CONFIRMATION`: any confirmed accepted relation.
2. `BOUNDARY_CONFIRMATION`: a raw confirmation whose support level is tied at the current accepted floor or ceiling.
3. `FRONTIER_ADVANCE`: a boundary confirmation that moves the accepted floor higher or the accepted ceiling lower versus the prior contiguous sealed bar.

An advance is never inferred across a source gap. Opposite-direction advances at different prices form a compound event, not a conflict.

## Inventory projection

The full relation inventory remains the machine-audit authority in the parent v0.3a stream. The review may expose a compact projection containing only:

- accepted floor and every tied floor ID;
- accepted ceiling and every tied ceiling ID;
- relation counts, challenged/refreshed counts and directional balance;
- exact youngest, median and oldest relation ages;
- boundary width and close position.

The projection may not discard the parent ledger, choose a hidden best level, introduce age buckets, or change lifecycle eligibility.

## Review boundary

The review compares event occupancy, duration, transition frequency, monthly rate stability, retained evidence, inventory size and genuine conflict. It may not read OPT-C outcomes, profitability, future bars, recommendations or execution data.

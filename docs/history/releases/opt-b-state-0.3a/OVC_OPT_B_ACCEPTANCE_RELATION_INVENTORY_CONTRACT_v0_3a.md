# OVC OPT-B Acceptance Relation-Inventory Contract v0.3a

**Contract ID:** `B-STATE-0.3a`  
**Parent candidate:** `B-STATE-0.3`  
**Relevance authority:** `B-REF-0.2-STRUCTURAL-ONLY`  
**Status:** `CONTROLLED REPLAY CANDIDATE — NOT RATIFIED`

## Semantic correction

Acceptance is not a categorical market state. `B-STATE-0.3a` removes
`ACCEPTED_ABOVE`, `ACCEPTED_BELOW` and `ACCEPTED_CORRIDOR` from the persistent
state vocabulary. The unchanged acceptance classifier produces:

1. a one-bar `acceptance_event_state`; and
2. level-specific maintained relations stored in an inventory.

Displacement, compression, interaction and quality remain independent axes
under the v0.3 contract. Acceptance cannot suppress them.

## Acceptance event

On the lawful `first_valid_time` bar:

- confirmed upward acceptance emits `ACCEPTED_ABOVE_EVENT`;
- confirmed downward acceptance emits `ACCEPTED_BELOW_EVENT`;
- both directions at different levels emit `COMPOUND_ACCEPTANCE_EVENT`;
- opposite directions for the same level or raw classifier ambiguity emit
  `CONFLICTING`;
- absence of new acceptance emits `NONE`.

The event lasts one bar. Consecutive event bars are separate lawful events, not
an indefinitely persistent state.

## Relation inventory

The v0.3 level-specific maintenance rules are unchanged. Every active relation
retains its level ID, direction, frozen `return_min`, latest supporting term
record IDs, challenge count and observed-bar age since refresh.

Each bar exposes:

- accepted-above, accepted-below, challenged and refreshed counts;
- every accepted-above and accepted-below level ID;
- the highest accepted-above price as the accepted floor;
- the lowest accepted-below price as the accepted ceiling;
- every tied level ID at either boundary;
- boundary width and the close's unbounded numeric position within it;
- youngest, median and oldest relation ages in observed closed bars;
- directional relation balance: `above_count - below_count`.

These are measurements, not labels, scores, recommendations or edge claims.
No level is selected as a hidden best level. Boundary extrema summarize the
inventory while every contributing relation remains present.

## Lifecycle and gaps

- One maintenance failure marks a relation challenged.
- Two consecutive failures end that relation.
- `RANGE_SUPERSEDED` ends the tied range relation.
- `ACCEPTED_THROUGH` stops new interaction eligibility but does not erase the
  relation created by the acceptance event.
- A gap resets pending failure counts and marks carried relations stale.
- No exit or freshness inference crosses a source gap.

No qualitative freshness buckets or TTLs exist in v0.3a. Freshness remains an
exact timestamp and observed-bar age so later semantic review cannot hide an
arbitrary threshold.

## Authority boundary

The contract may read sealed OPT-A bars, the ratified structural lifecycle and
frozen OPT-B term records. It may not read OPT-C outcomes, profitability,
future bars, recommendations or execution data. Historical replay does not
ratify or activate the contract.


# OVC OPT-B Acceptance Frontier State Contract v0.3b

**Contract ID:** `B-STATE-0.3b`  
**Ratification ID:** `B-STATE-0.3b-FRONTIER-ACTIVE-RESEARCH`  
**Status:** `RATIFIED FOR ACTIVE OPT-B RESEARCH STATE`  
**Representation authority:** `B-STATE-0.3a-REPRESENTATION-ONLY`

## Primary acceptance event

The acceptance axis is event-based and non-persistent. For a contiguous sealed
bar, a lawful raw acceptance confirmation is promoted only when its support
level is tied at and advances the accepted frontier:

- `FRONTIER_ADVANCE_UP`: the current accepted floor is higher than the prior
  accepted floor, or establishes the first floor within a contiguous segment;
- `FRONTIER_ADVANCE_DOWN`: the current accepted ceiling is lower than the prior
  accepted ceiling, or establishes the first ceiling within a contiguous segment;
- `COMPOUND_FRONTIER_ADVANCE`: both directions occur at different valid prices;
- `CONFLICTING`: the classifier contradicts itself at one level or the frontier
  bounds are invalid;
- `NONE`: no lawful frontier advance occurs.

The event lasts one bar and is recomputed from current evidence. A gap prohibits
comparison with the prior segment and therefore cannot manufacture an advance.

## Evidence layers

- Raw confirmation: retained in the manifest-bound v0.3a parent ledger.
- Boundary confirmation: retained in the v0.3b semantic-review evidence.
- Frontier advance: primary acceptance event in the active research state.

No evidence layer may suppress displacement, compression, interaction or
quality axes.

## Default frontier projection

The state stream exposes accepted floor/ceiling prices and tied IDs, boundary
width, close position, relation counts, challenged/refreshed counts, exact age
statistics and directional balance.

Every row also exposes the canonical hash of the complete parent relation
inventory and the parent state-record ID. The complete inventory remains
machine authority. The compact projection cannot rank, prune, expire or choose
a hidden best relation.

## Authority boundary

The contract may read sealed OPT-A bars and ratified OPT-B structural evidence.
It may not read OPT-C outcomes, future bars, profitability, recommendations,
risk decisions or execution data. Ratification is research-state authority only.

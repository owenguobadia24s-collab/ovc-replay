# OVC OPT-B Parallel-Axis State Contract v0.3

**Contract ID:** `B-STATE-0.3`  
**Relevance authority:** `B-REF-0.2-STRUCTURAL-ONLY`  
**Status:** `CONTROLLED REPLAY CANDIDATE — NOT RATIFIED`

## Semantic correction

`B-STATE-0.3` does not force heterogeneous OPT-B terms into one exclusive
state. Every closed bar has five independently resolved fields:

1. `location_state`: level-relative acceptance conditions;
2. `displacement_state`: directional impulse persistence;
3. `compression_state`: compression persistence;
4. `interaction_state`: one-bar reclaim, rejection and breach/response events;
5. `quality_state`: coherence, genuine conflict and post-gap staleness.

No field suppresses evidence in another field. There is no global precedence
between acceptance, reclaim, rejection, displacement and compression.

## Location axis

The existing `B.TERM.ACCEPTANCE.v0.1` classifier remains frozen. A confirmed
acceptance event creates or refreshes a condition for its own reference level.
The condition retains all same-time supporting record IDs and uses the strictest
frozen `return_min` among them.

On each later contiguous closed bar:

- accepted above is maintained when `close >= level_price + return_min`;
- accepted below is maintained when `close <= level_price - return_min`;
- one failure marks that level condition challenged;
- two consecutive failures end that level condition;
- a fresh same-direction acceptance refreshes it;
- a fresh opposite acceptance replaces it only when unambiguous.

`ACCEPTED_THROUGH` retirement prevents future interaction eligibility but does
not erase the acceptance relation that caused retirement. A separate
`RANGE_SUPERSEDED` retirement ends an existing location condition.

Several accepted-above levels or accepted-below levels form one compound
location state. Accepted above lower levels and accepted below higher levels
form `ACCEPTED_CORRIDOR`, not conflict. Inverted bounds or contradictory
acceptance for the same level are genuine conflicts.

## Displacement and compression axes

Displacement persists independently until two consecutive non-advancing closes
against its direction. A fresh displacement refreshes or changes the axis.
Opposite displacement confirmations on one bar are genuine conflict.

Compression persists independently until two consecutive failed compression
evaluations. Compression and displacement may coexist on the same bar.

## Interaction axis

Confirmed reclaim, rejection and reference-level breach/response records are
one-bar events. Same-label evidence retains every support level and record ID.
Different interactions at different levels may coexist as `COMPOUND`; they do
not conflict merely because their directions differ. Raw classifier ambiguity
or opposite directions for the same interaction family and level are genuine
conflict.

## Gaps and quality

No exit counter crosses a source gap. Persistent axes are carried as stale,
their pending exit counters reset, and each axis must receive positive
maintenance evidence or exit before it ceases to be stale. A gap cannot create
neutrality.

## Timing and authority

Only evidence at `first_valid_time` may update state. All level-dependent terms
must have anchors relevant under `B-REF-0.2-STRUCTURAL-ONLY`. The contract uses
no OPT-C outcomes, profitability, future bars, edge claims or execution input.


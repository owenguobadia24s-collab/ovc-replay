# OVC OPT-B Deterministic Term Contracts v0.1

**Status:** DRAFT FOR REPLAY VALIDATION — NOT ACTIVE  
**Registry:** `OPT-B-LANGUAGE`  
**Registry version:** `B-LANG-0.1`  
**Initial instrument:** GBP/USD  
**Initial clocks:** 15M detail; 2H story aggregation  
**Horizon:** classification only; outcomes remain in `OPT-C`  
**Authority:** none until replay validation and operator approval

---

## 1. Contract boundary

These contracts make the first seven OVC operating terms deterministic:

1. `COMPRESSION`
2. `DISPLACEMENT`
3. `REFERENCE_LEVEL_BREACH_AND_RESPONSE` — operator alias: `SWEEP`
4. `RECLAIM`
5. `ACCEPTANCE`
6. `REJECTION`
7. `TRANSITION`

They describe observable price behaviour. They do not claim participant intent, predict an outcome, establish an edge, or authorize a trade.

Every result is calculated only from data whose source bar has closed. No contract may be rewritten after an `OPT-C` outcome becomes known.

---

## 2. Shared data contract

### 2.1 Required `OPT-A` inputs

For each canonical bar `b_t`:

```yaml
instrument_id: string
timeframe: 15M|2H
open_time_utc: timestamp
close_time_utc: timestamp
open: decimal
high: decimal
low: decimal
close: decimal
source_id: string
source_release_id: string
bar_status: CLOSED|INCOMPLETE|QUARANTINED
price_increment: decimal
```

Volume is optional and is not used by `B-LANG-0.1`.

### 2.2 Bar admissibility

A bar is admissible only when:

- `bar_status = CLOSED`;
- OHLC values are finite and positive;
- `high >= max(open, close)`;
- `low <= min(open, close)`;
- `high >= low`;
- the expected preceding bars required by the contract exist without a session/calendar gap classified as missing data;
- the source release has not been quarantined.

Otherwise the result is `NOT_EVALUABLE` with a reason code. Missing values are never forward-filled.

### 2.3 Arithmetic rules

- Calculations use decimal arithmetic at the provider’s source precision.
- Comparisons use `epsilon = price_increment`.
- Ratios are retained to at least 8 decimal places.
- A zero denominator yields `NOT_EVALUABLE`, never infinity.
- Threshold equality passes: `>=` and `<=` are inclusive as written.

### 2.4 Shared primitives

For closed bar `t`:

```text
R_t       = H_t - L_t
BODY_t    = abs(C_t - O_t)
DIR_t     = +1 if C_t > O_t; -1 if C_t < O_t; 0 otherwise
TR_t      = max(H_t - L_t, abs(H_t - C_(t-1)), abs(L_t - C_(t-1)))
ATR20_t   = arithmetic_mean(TR_(t-19) ... TR_t)
BODY_FRAC = BODY_t / R_t
```

Directional close location:

```text
CLV_UP_t   = (C_t - L_t) / R_t
CLV_DOWN_t = (H_t - C_t) / R_t
```

Close-path efficiency over `n` bars ending at `t`:

```text
EFF(n,t) = abs(C_t - C_(t-n)) / sum(i=t-n+1..t, abs(C_i - C_(i-1)))
```

Consecutive-bar overlap:

```text
OVERLAP(i,j) = max(0, min(H_i,H_j) - max(L_i,L_j))
UNION(i,j)   = max(H_i,H_j) - min(L_i,L_j)
OVERLAP_FRAC(i,j) = OVERLAP(i,j) / UNION(i,j)
```

All ATR-normalized thresholds use `ATR20_(t-1)` or the ATR value frozen at the event anchor. This prevents the candidate bar or later response bars from enlarging their own baseline.

### 2.5 Evaluation clocks

Each contract is evaluated independently on:

- canonical closed 15M bars; and
- canonical closed 2H bars.

A 2H term is never inferred merely because its constituent 15M bars contain that term. Cross-clock relationships are separate derived records.

### 2.6 Common result envelope

```yaml
term_record_id: deterministic UUID/hash
term_id: string
term_version: B-LANG-0.1
instrument_id: string
timeframe: 15M|2H
direction: UP|DOWN|NONE
anchor_time: timestamp
first_valid_time: timestamp
evaluated_at: timestamp
status: PENDING|CONFIRMED|FAILED|AMBIGUOUS|NOT_EVALUABLE
measurements: object
reference_level_id: string|null
input_bar_ids: [string]
source_release_id: string
parameter_set_id: B-LANG-0.1-SEED
reason_codes: [string]
```

`anchor_time` identifies when the behaviour began. `first_valid_time` is the earliest moment the classification could lawfully have been known. Backtests must join predictions using `first_valid_time`, not `anchor_time`.

---

## 3. Reference-level contract

Level-dependent terms require a level created before the candidate event.

```yaml
reference_level_id: string
level_type: PRIOR_SWING_HIGH|PRIOR_SWING_LOW|RANGE_HIGH|RANGE_LOW|PDH|PDL|PWH|PWL|PMH|PML|IBH|IBL|VAH|VAL|POC|EQUILIBRIUM|FVG_BOUNDARY|CUSTOM_RESEARCH
price: decimal
created_at: timestamp
first_valid_time: timestamp
construction_rule_id: string
construction_rule_version: string
source_bar_ids: [string]
status: ACTIVE|RETIRED|INVALID
```

Rules:

- `first_valid_time < candidate anchor_time`;
- the construction rule must be deterministic and versioned;
- `CUSTOM_RESEARCH` levels cannot enter an active operator surface;
- a level cannot be moved after interaction begins;
- multiple eligible levels produce separate term records, not a silently chosen “best” level.

Seed tolerances frozen at event anchor `a`:

```text
ATR_A       = ATR20_(a-1)
TOUCH_TOL   = max(2 * epsilon, 0.05 * ATR_A)
BREACH_MIN  = max(2 * epsilon, 0.10 * ATR_A)
RETURN_MIN  = max(2 * epsilon, 0.10 * ATR_A)
DEPART_MIN  = max(4 * epsilon, 0.50 * ATR_A)
```

---

## 4. `COMPRESSION`

**Contract ID:** `B.TERM.COMPRESSION.v0.1`  
**Role:** condition  
**Direction:** `NONE`

### 4.1 Parameters

```yaml
window_bars: 8
baseline_bars: 20
median_tr_ratio_max: 0.70
span_atr_max: 2.00
mean_overlap_min: 0.55
efficiency_max: 0.35
```

The baseline window is the 20 bars immediately preceding the 8-bar candidate window.

### 4.2 Formula

For candidate window `W = [t-7, t]` and baseline `Q = [t-27, t-8]`:

```text
TR_RATIO      = median(TR in W) / median(TR in Q)
WINDOW_SPAN   = max(H in W) - min(L in W)
SPAN_ATR      = WINDOW_SPAN / ATR20_(t-8)
MEAN_OVERLAP  = mean(OVERLAP_FRAC(i-1,i), i=t-6..t)
PATH_EFF      = EFF(7,t)
```

`COMPRESSION = CONFIRMED` iff all are true:

```text
TR_RATIO     <= 0.70
SPAN_ATR     <= 2.00
MEAN_OVERLAP >= 0.55
PATH_EFF     <= 0.35
```

### 4.3 Timing and state

- `anchor_time = close_time_(t-7)`
- `first_valid_time = close_time_t`
- The condition remains active while a rolling 8-bar window continues to pass.
- It ends at the first closed bar whose rolling window fails any two thresholds, or after two consecutive bars fail any one threshold.
- A single-threshold, single-bar failure yields `PENDING_EXIT`, represented as `PENDING` in the common envelope with reason `COMPRESSION_EXIT_UNCONFIRMED`.

### 4.4 Ambiguity and exclusions

- If the baseline median TR is zero: `NOT_EVALUABLE`.
- If the window contains a missing/quarantined bar: `NOT_EVALUABLE`.
- Compression does not mean accumulation, distribution, coiled energy, or future breakout.

---

## 5. `DISPLACEMENT`

**Contract ID:** `B.TERM.DISPLACEMENT.v0.1`  
**Role:** event  
**Direction:** `UP` or `DOWN`

### 5.1 Parameters

```yaml
true_range_atr_min: 1.50
body_fraction_min: 0.65
close_location_min: 0.80
close_travel_atr_min: 0.80
```

### 5.2 Formula

For candidate bar `t`, using `ATR = ATR20_(t-1)`:

```text
TR_ATR       = TR_t / ATR
CLOSE_TRAVEL = abs(C_t - C_(t-1)) / ATR
```

Upward displacement is confirmed iff:

```text
DIR_t = +1
TR_ATR >= 1.50
BODY_FRAC_t >= 0.65
CLV_UP_t >= 0.80
CLOSE_TRAVEL >= 0.80
```

Downward displacement is symmetric using `DIR_t = -1` and `CLV_DOWN_t`.

### 5.3 Timing

- `anchor_time = open_time_t`
- `first_valid_time = close_time_t`
- No intrabar displacement is emitted in `v0.1`.

### 5.4 Ambiguity and exclusions

- A doji cannot qualify.
- If both directional rules appear true because of corrupt data: `AMBIGUOUS` and quarantine the input.
- Displacement does not by itself mean breakout, acceptance, initiative order flow, or continuation.

---

## 6. `REFERENCE_LEVEL_BREACH_AND_RESPONSE`

**Contract ID:** `B.TERM.REFERENCE_LEVEL_BREACH_RESPONSE.v0.1`  
**Operator alias:** `SWEEP`  
**Role:** event sequence  
**Direction:** `UP` for breach above a level; `DOWN` for breach below

### 6.1 Parameters

```yaml
response_window_bars: 4
breach_min_atr: 0.10
return_min_atr: 0.10
acceptance_exclusion: true
```

### 6.2 Upward breach rule

For high-side reference price `P_REF` and first candidate bar `a`:

```text
H_a >= P_REF + BREACH_MIN
```

On the first such close, emit `PENDING` anchored to `a`.

Confirm at the earliest bar `r in [a, a+3]` where:

```text
C_r <= P_REF - RETURN_MIN
```

and `ACCEPTANCE_ABOVE(P_REF)` has not been confirmed using bars from `a` through `r`.

### 6.3 Downward breach rule

Symmetrically:

```text
L_a <= P_REF - BREACH_MIN
C_r >= P_REF + RETURN_MIN
```

with no confirmed `ACCEPTANCE_BELOW(P_REF)`.

### 6.4 Resolution

- `anchor_time = close_time_a`
- `first_valid_time = close_time_r` when confirmed
- If the response is not confirmed by `close_time_(a+3)`: `FAILED`
- If acceptance is confirmed first: `FAILED` with `ACCEPTED_BEYOND_LEVEL`
- If both return and acceptance would become valid on the same close under overlapping windows: `AMBIGUOUS`; neither downstream interpretation may use it.

### 6.5 Meaning boundary

The term records a breach and measurable response. It does not assert that stops, liquidity, or traders were intentionally targeted.

---

## 7. `RECLAIM`

**Contract ID:** `B.TERM.RECLAIM.v0.1`  
**Role:** event sequence  
**Direction:** side regained: `UP` means price regains above; `DOWN` means price regains below

### 7.1 Preconditions

A reclaim requires a prior confirmed close on the lost side of reference price `P_REF`:

- upward reclaim candidate: at least one close `<= P_REF - TOUCH_TOL` in the preceding 8 bars;
- downward reclaim candidate: at least one close `>= P_REF + TOUCH_TOL` in the preceding 8 bars.

### 7.2 Parameters

```yaml
lookback_bars_for_lost_side: 8
confirmation_window_bars: 3
minimum_confirming_closes: 2
reclaim_distance_atr: 0.10
```

### 7.3 Upward reclaim

The first bar `a` with:

```text
C_a >= P_REF + RETURN_MIN
```

creates `PENDING`. It becomes `CONFIRMED` at the earliest `r <= a+2` when at least two closes among `[a,r]` are `>= P_REF + RETURN_MIN`, including `C_r`.

Downward reclaim is symmetric with closes `<= P_REF - RETURN_MIN`.

### 7.4 Resolution

- `anchor_time = close_time_a`
- `first_valid_time = close_time_r`
- If two confirming closes do not occur within three bars: `FAILED`
- If both upward and downward reclaim candidates for the same level overlap: both are `AMBIGUOUS`
- Reclaim describes regained price location; it does not imply a lasting trend change.

---

## 8. `ACCEPTANCE`

**Contract ID:** `B.TERM.ACCEPTANCE.v0.1`  
**Role:** condition  
**Direction:** `UP` means accepted above; `DOWN` means accepted below

### 8.1 Parameters

```yaml
window_bars: 4
minimum_closes_beyond: 3
terminal_close_must_be_beyond: true
distance_atr: 0.10
maximum_opposite_excursion_atr: 0.25
```

All distances use the ATR frozen at the first bar of the four-bar window.

### 8.2 Acceptance above

For window `W = [t-3,t]` and reference price `P_REF`, acceptance above is confirmed iff:

```text
count(C_i >= P_REF + RETURN_MIN, i in W) >= 3
C_t >= P_REF + RETURN_MIN
min(L_i, i in W) >= P_REF - 0.25 * ATR_A
```

Acceptance below is symmetric:

```text
count(C_i <= P_REF - RETURN_MIN, i in W) >= 3
C_t <= P_REF - RETURN_MIN
max(H_i, i in W) <= P_REF + 0.25 * ATR_A
```

### 8.3 Timing and state

- `anchor_time = close_time_(t-3)`
- `first_valid_time = close_time_t`
- Acceptance remains active while at least two of the latest three closes remain on the accepted side and no opposite reclaim is confirmed.
- It ends when an opposite reclaim confirms or two consecutive closes finish on the non-accepted side of `P_REF`.

### 8.4 Exclusions

Acceptance is price-time acceptance under this contract. Without volume-at-price data it is not volume acceptance and must not be described as such.

---

## 9. `REJECTION`

**Contract ID:** `B.TERM.REJECTION.v0.1`  
**Role:** event sequence  
**Direction:** direction of departure from the level

### 9.1 Parameters

```yaml
interaction_tolerance_atr: 0.05
response_window_bars: 4
departure_atr_min: 0.50
acceptance_exclusion: true
```

### 9.2 Rejection downward from a high-side level

Interaction begins at first bar `a` satisfying:

```text
H_a >= P_REF - TOUCH_TOL
```

Emit `PENDING`. Confirm `DOWN` at earliest `r in [a,a+3]` where:

```text
C_r <= P_REF - DEPART_MIN
```

provided `ACCEPTANCE_ABOVE(P_REF)` has not confirmed.

### 9.3 Rejection upward from a low-side level

Symmetrically:

```text
L_a <= P_REF + TOUCH_TOL
C_r >= P_REF + DEPART_MIN
```

with no `ACCEPTANCE_BELOW(P_REF)`.

### 9.4 Resolution

- `anchor_time = close_time_a`
- `first_valid_time = close_time_r`
- No qualifying departure within four bars: `FAILED`
- Acceptance first: `FAILED` with `ACCEPTED_AT_LEVEL`
- A breach-and-response may also qualify as rejection. Both records may exist because one describes boundary traversal and the other departure magnitude; their shared input IDs must be retained.

---

## 10. `TRANSITION`

**Contract ID:** `B.TERM.TRANSITION.v0.1`  
**Role:** state change  
**Direction:** `UP`, `DOWN`, or `NONE` according to destination state

### 10.1 State vocabulary

`B-LANG-0.1` permits only these derived states:

```text
NEUTRAL
COMPRESSED
DISPLACING_UP
DISPLACING_DOWN
ACCEPTED_ABOVE:<level_id>
ACCEPTED_BELOW:<level_id>
REJECTED_UP:<level_id>
REJECTED_DOWN:<level_id>
RECLAIMED_ABOVE:<level_id>
RECLAIMED_BELOW:<level_id>
AMBIGUOUS
```

### 10.2 State precedence

When multiple confirmed terms share a `first_valid_time`, choose state by this precedence:

1. `AMBIGUOUS`
2. `ACCEPTED_*`
3. `RECLAIMED_*`
4. `REJECTED_*`
5. `DISPLACING_*`
6. `COMPRESSED`
7. `NEUTRAL`

Precedence selects the current state for the state machine; it does not delete the lower-precedence term records.

### 10.3 Transition rule

A transition is confirmed when:

```text
previous_state != destination_state
previous_state was the resolved state on at least 2 consecutive closed bars
destination_state is produced by a CONFIRMED term
neither state is AMBIGUOUS
```

The transition record contains:

```yaml
from_state: string
to_state: string
trigger_term_record_ids: [string]
previous_state_first_valid_time: timestamp
destination_state_first_valid_time: timestamp
```

### 10.4 Timing

- `anchor_time = destination term's anchor_time`
- `first_valid_time = destination term's first_valid_time`
- A move into `AMBIGUOUS` is recorded as a state-quality event, not a market transition.
- `NEUTRAL -> <state>` and `<state> -> NEUTRAL` are valid transitions.

### 10.5 Meaning boundary

A transition is a deterministic change in the active `OPT-B` state. It does not automatically mean `CHoCH`, reversal, regime change, or `STORY-D`.

---

## 11. Inter-term consistency rules

| Situation | Required handling |
|---|---|
| Compression and displacement confirm on the same bar | Retain both term records; state resolves to displacement; emit `COMPRESSION_RELEASE_CANDIDATE` only as a research relation |
| Acceptance and rejection of the same side/level overlap | Mark both `AMBIGUOUS` unless one became valid strictly earlier |
| Acceptance and breach-response overlap | Earlier first-valid record stands; later incompatible record becomes `FAILED` |
| Reclaim occurs after breach-response | Retain both; link reclaim as subsequent behaviour, not duplicate evidence |
| Several levels qualify | Create one record per level and expose multiplicity |
| Opposite-direction events confirm simultaneously | Mark directional state `AMBIGUOUS`; retain raw term records |
| A term is recomputed under changed parameters | Create a new term version; never mutate the old record |

---

## 12. Deterministic IDs and reproducibility

`term_record_id` is the hash of the canonical serialization of:

```text
term_id
term_version
instrument_id
timeframe
direction
anchor_time
first_valid_time
reference_level_id or null
ordered input_bar_ids
parameter_set_id
source_release_id
```

The same inputs and code release must produce the same ID and measurements.

Each run records:

- code commit/build ID;
- parameter-set hash;
- source release and bar IDs;
- timezone/session calendar version;
- arithmetic implementation version;
- result counts by status and reason code.

---

## 13. Required replay tests

### 13.1 Unit fixtures per term

Each term requires at least:

- one exact-threshold pass;
- one just-below-threshold fail;
- bullish/upward and bearish/downward symmetry cases where applicable;
- zero-range and missing-bar cases;
- price-increment boundary cases;
- overlapping-term ambiguity cases;
- a first-valid-time assertion;
- a no-lookahead assertion.

### 13.2 Property tests

- Changing bars after `first_valid_time` cannot alter the original record.
- Mirroring prices around a constant produces the symmetric directional result.
- Re-running identical inputs produces byte-equivalent canonical output.
- Shuffling input order fails validation rather than changing the result silently.
- An outcome field presented to the classifier is ignored or rejected.

### 13.3 Historical replay gates

Before operator activation:

1. run the full selected GBP/USD history;
2. inspect frequency by year, session, and clock;
3. sample at least 30 positives and 30 near-miss negatives per term where available;
4. inspect all `AMBIGUOUS` clusters;
5. measure sensitivity around every seed threshold;
6. compare 15M and 2H classifications without conflating them;
7. freeze results and counterexamples in `OPT-D`;
8. approve, revise as a new version, or reject each term separately.

No target hit rate or profitable outcome is a term-activation requirement. Term quality means semantic fidelity, determinism, timing correctness, and replay stability. Edge testing occurs later against `OPT-C` outcomes through `OPT-D` studies.

---

## 14. Seed-parameter warning

The numerical thresholds in `B-LANG-0.1-SEED` are deterministic starting hypotheses, not claims of market truth. They were selected to make the terms executable and falsifiable.

Threshold research must:

- use a declared discovery interval;
- publish sensitivity surfaces rather than only the best value;
- keep untouched validation data;
- avoid optimizing all seven terms jointly against profitability;
- create a new registry/parameter version for every accepted change;
- preserve rejected and superseded parameter sets.

---

## 15. Promotion states

Each contract progresses independently:

```text
DRAFTED
  -> UNIT_VALIDATED
  -> HISTORICALLY_REPLAYED
  -> SEMANTICALLY_REVIEWED
  -> OPERATOR_APPROVED
  -> ACTIVE_RESEARCH
```

`ACTIVE_RESEARCH` permits use in Path 1, Path 2, `OPT-C` joins, and `OPT-D` studies. It does not make the term an edge, playbook, or execution signal.

The current state of all seven contracts is `DRAFTED`.

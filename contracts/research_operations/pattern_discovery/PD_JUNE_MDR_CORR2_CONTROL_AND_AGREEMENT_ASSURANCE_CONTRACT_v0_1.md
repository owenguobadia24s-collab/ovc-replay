# PD-JUNE-MDR-CORR2 Control and Agreement Assurance Contract v0.1

## 1. Identity

- Programme: `OVC-PD-JUNE-2026-OPERATOR-REVIEW-AND-MARKET-DESCRIPTION-ASSURANCE.v0.1`
- Packet: `PD-JUNE-MDR-CORR2-CONTROL-AND-AGREEMENT-ASSURANCE`
- Baseline main: `1d436299c770a7043f95d7772b7550526de3ec73`
- Parent decision: `PD-JUNE-MDR-G1` — operator `DEFER`
- Source pilot: `PD.PILOT.RUN.96c16f11717e787f971851ee`
- Source slice: `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`

## 2. Purpose

CORR2 measures bounded false-positive behaviour and repeat-review stability for the exact June pilot evidence. It does not change the market model and cannot establish a general reliability claim beyond the exact gapped slice.

## 3. Authority

Authorised:

1. deterministic read-only control construction from existing June C2 states and 15M price bars;
2. a blinded review packet containing the six queue-promoted candidates and a predeclared stratified control sample;
3. scoring of a completed operator response;
4. QA, evidence receipts and a return packet for `PD-JUNE-MDR-G1`.

Denied:

- provider intake or another replay;
- candidate insertion, mutation or relabelling;
- canonical Discovery processing or append;
- formula, semantic, trigger, candidate, distance, cluster, threshold or model changes;
- promotion, selector or release mutation;
- R2 publication or Validation consumption;
- probability, risk, exposure, trading, execution or agent write.

## 4. Control eligibility

A control is eligible only when all conditions hold:

1. it is a contiguous sequence in one exact 15M side-and-scope C2 stream;
2. consecutive `first_valid_time` values differ by exactly 15 minutes;
3. none of its C2 state IDs appears in `source_c2_record_ids` for any of the 208 immutable candidates;
4. selected controls are mutually disjoint by C2 state identity;
5. exact source state and price bytes are hash-bound.

## 5. Matched controls

One matched control is selected for each promoted candidate.

The control must preserve:

- side;
- evaluation scope;
- duration;
- `QUALITY`-axis sequence where an exact eligible match exists.

Ranking is deterministic:

1. minimum `QUALITY` mismatch count;
2. minimum absolute start-time distance from the promoted candidate;
3. ascending SHA-256 tie break over promoted ID and control state IDs.

## 6. Population controls

One four-record control is selected for each of the four 15M side-and-scope strata. The eligible disjoint window with the minimum SHA-256 rank is selected.

The final blinded set contains:

- 6 promoted candidates;
- 6 matched noncandidate controls;
- 4 population noncandidate controls;
- 16 cards total.

## 7. Blinding

The visible review card excludes:

- source object identity;
- candidate/control class;
- prior operator disposition;
- machine trigger label;
- exact C2 state IDs.

It preserves exact market timestamps, side, scope, OHLC and structural evidence required for a genuine review. Card order is deterministic but identity-blinded.

The sealed answer key must not be opened before the review response is complete.

## 8. Required operator response

Every card requires:

- `trigger_classification`;
- `structural_description_verdict`;
- `review_disposition`;
- confidence from 1 to 5;
- contradiction codes and notes.

Missing, duplicate, altered or invalid responses fail closed.

## 9. Predeclared scoring

A bounded exact-June PASS requires all of:

- all 16 cards completed;
- at least 8 of 10 controls have determinate classifications;
- zero false-positive trigger classifications among determinate controls;
- at least 5 of 6 promoted objects are classified as trigger-present;
- at least 4 of 6 promoted trigger reasons match exactly;
- zero promoted structural contradictions;
- at least 4 of 6 repeat dispositions agree with the prior final operator disposition;
- Cohen's kappa for disposition agreement is at least 0.40.

Failure does not authorise a model change. It returns `DEFER` or `BLOCK` evidence to `PD-JUNE-MDR-G1`.

Even a bounded PASS leaves general market-description reliability as `NOT_ESTABLISHED_SINGLE_GAPPED_JUNE_SLICE`.

## 10. Stop condition

CORR2 stops after the blinded review input, answer key, response template, tests and QA are materialised. The operator must complete the blinded response. Automation must not invent or substitute operator judgments.

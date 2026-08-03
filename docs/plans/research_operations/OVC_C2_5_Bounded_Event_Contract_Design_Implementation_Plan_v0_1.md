# OVC C2.5 Bounded Event Contract Design Implementation Plan v0.1

## 1. Identity and authority

- **Programme ID:** `OVC-C2.5-BOUNDED-EVENT-CONTRACT-v0.1`
- **Plan ID:** `OVC-C2.5-BOUNDED-EVENT-CONTRACT-DESIGN-IMPLEMENTATION-PLAN-0.1`
- **Source authority:** `MTA-G8-C2.5=PASS`
- **Source decision:** `MTA-G8.OPERATOR.MULTIPART.20260803T114000+0100`
- **Initial gate:** `C25-G0`
- **Current status:** `GATE_READY`
- **Authority available now:** preparation of this plan and its gate packet only
- **Authority denied now:** event promotion, event activation, marker redefinition, formula or threshold change, candidate or semantic authority

`C25-G0` is operator-required. The approved MTA decision authorises one bounded design programme for four named rules only. It does not make those rules events.

## 2. Purpose

Determine whether four existing frozen research-selection rules can support explicit, first-valid, non-semantic event contracts without altering their formulas, thresholds or current research-selection role.

The bounded rules are:

1. `BOUNDARY_ZONE_ENTRY`
2. `BREACH_ACTIVE`
3. `LONG_PERSISTENCE`
4. `REPEATED_SWITCHING`

The programme must expose the complete evidence and computability profile for each rule. It must not collapse evidence into a single readiness badge.

The core question is not “does the rule look useful?” It is:

> Can each occurrence be represented as a deterministic, first-valid, reproducible structural event record with explicit prerequisites, deduplication, episode linkage, termination and censoring—without semantic or predictive promotion?

## 3. Explicitly excluded rules

The following rules are outside this programme and must remain unavailable to contract generation:

- `RETURN_INSIDE` — `DEFER_ZERO_FIRES`
- `COMPRESSION_TO_DISPLACEMENT` — `DEFER_ZERO_FIRES`
- `LOCAL_PARENT_CONFLICT` — `BLOCK_NOT_EVALUABLE`
- `ALIGNMENT_GAINED` — `BLOCK_NOT_EVALUABLE`

Adding any excluded rule is scope expansion and requires a new operator decision.

## 4. Binding baseline evidence

The programme inherits the accepted full-population evidence:

| Rule | Attempted | Evaluable | Fired | Evaluable rate | Fire rate among evaluable |
|---|---:|---:|---:|---:|---:|
| `BOUNDARY_ZONE_ENTRY` | 7,116 | 4,556 | 388 | 64.024733% | 8.516242% |
| `BREACH_ACTIVE` | 7,116 | 6,226 | 588 | 87.492974% | 9.444266% |
| `LONG_PERSISTENCE` | 7,116 | 4,644 | 306 | 65.261383% | 6.589147% |
| `REPEATED_SWITCHING` | 7,116 | 4,204 | 316 | 59.078134% | 7.516651% |

Additional constraints:

- 26,516 of 56,928 rule attempts are `NOT_EVALUABLE` across all eight frozen rules;
- 7,116 windows collapse to 1,779 centre-time occurrences;
- the primary overlap rule yields 20 connected components;
- zero occurrences classify `ROBUST` across all three frozen overlap variants;
- C2 quality is never COMPLETE in the accepted population;
- C2E is still inactive and its neutral episode plan requires separate operator approval.

These values are evidence inputs, not event acceptance thresholds.

## 5. Scope

### 5.1 Included

- the four bounded rules only;
- current formulas and thresholds exactly as frozen;
- deterministic occurrence records over accepted June evidence;
- first-valid timestamp audit;
- explicit evaluability prerequisites and reason codes;
- occurrence deduplication across BID/ASK and local/parent scopes;
- strict, primary and permissive overlap sensitivity;
- neutral C2E episode linkage as an optional reference once a lawful C2E shadow exists;
- read-only contract inspection;
- QA, gate packets, programme state and rollback.

### 5.2 Excluded

- changes to formulas, thresholds, windows or source clocks;
- treating a fired rule as a market event before final operator approval;
- semantic names, directional meaning, probability or prediction;
- candidate, family, model, selector or theory promotion;
- outcome joins, backtest performance or trading relevance;
- C3 structural meaning;
- new rules, instruments, markets, sides, providers or dependencies;
- Validation consumption, R2 publication, risk, exposure or execution.

## 6. Event-contract design standard

Each draft contract must be decomposable and include:

- `rule_id` and frozen rule version;
- exact formula and threshold references without duplication or amendment;
- required C2 axes, relations, history and parent inputs;
- evaluability decision tree;
- first-valid timestamp definition;
- occurrence identity function;
- start condition and confirmation state;
- continuation and termination conditions;
- reset and censoring behavior;
- deduplication and overlap handling;
- strict, primary and permissive sensitivity results;
- optional neutral episode linkage with fail-closed behavior when C2E is unavailable;
- source identities, hashes and algorithm version;
- evidence counts and reason distributions;
- authority labels `DRAFT_CONTRACT`, `NON_SEMANTIC`, `NON_PREDICTIVE`, `NON_PROMOTED`.

A contract must display criterion-level results. A single `READY_FOR_EVENT_CONTRACT` badge is prohibited.

## 7. Rule-specific design questions

### 7.1 `BOUNDARY_ZONE_ENTRY`

- Is entry first-valid at the first evaluated LOCATION transition into a frozen boundary zone?
- How are persistent occupancy and repeated re-entry distinguished?
- Which resets and missing local ranges censor entry detection?
- How are BID/ASK paired occurrences represented without doubling independent evidence?

### 7.2 `BREACH_ACTIVE`

- Is breach first-valid at the first evaluated INTERACTION transition to active breach?
- How are continued breach, re-breach and immediate reversal represented?
- Is the breached level identity stable and source-addressable?
- What proportion of fired records collapse into the same overlap component?

### 7.3 `LONG_PERSISTENCE`

- Is the event first-valid when the frozen persistence counter first crosses its existing rule condition?
- Does the record identify the state being persisted and its uninterrupted lineage?
- How do resets, axis not-evaluable states and clock boundaries censor the counter?
- How is continued persistence prevented from producing duplicate event starts?

### 7.4 `REPEATED_SWITCHING`

- Is the event first-valid when the frozen switching condition is first satisfied?
- Is the switch history reproducible from accepted transition IDs?
- How are overlapping rolling histories deduplicated?
- Does sensitivity to window adjacency prevent an independent occurrence claim?

## 8. Dependency on C2E

C2.5 design may proceed independently using accepted C2 identities and MTA occurrence clusters. However:

- no contract may require C2E until the neutral episode contract is separately approved and materialized;
- missing C2E linkage is reported as `NOT_AVAILABLE`, not inferred;
- C2E episodes do not grant event authority;
- C2.5 activation is blocked unless episode linkage requirements, if adopted, are satisfied by an accepted versioned C2E source;
- C2E and C2.5 final gates remain independent.

## 9. Performance and artifact contract

Each packet is bounded to four hours local runtime and 10GB external artifact size. Long scans checkpoint every 30 minutes. `CAPACITY_EXCEEDED` preserves partial partitions and stops without changing formulas, thresholds or population definitions.

No raw market data, caches or full event populations are committed to Git.

## 10. Work packets

### C25-00 — Design contract and boundary freeze

Deliver:

- bounded rule registry;
- excluded-rule registry;
- event-contract schema;
- evidence-display contract;
- occurrence identity and deduplication contract;
- C2E dependency contract;
- performance and artifact contract;
- `C25-G0` operator packet.

**Gate `C25-G0`: OPERATOR_REQUIRED.** PASS authorises draft-contract implementation and shadow evaluation only. It does not promote any rule.

### C25-WP1 — Rule evidence profiles

For each bounded rule, reproduce:

- attempted, evaluable, fired, not-fired and not-evaluable counts;
- all reason codes;
- first-valid timestamp candidates;
- source-level and state-level prerequisites;
- overlap-component membership;
- BID/ASK and local/parent duplication;
- week, A–L block and reset-proximity distributions.

Any mismatch with MTA-WP5 blocks continuation.

### C25-WP2 — Draft contract materialization

Create a versioned draft contract for each bounded rule. Contracts reference the frozen rule implementation rather than copying or modifying formulas. Fixtures cover:

- valid first fire;
- continued condition without duplicate start;
- reset censoring;
- not-evaluable prerequisites;
- identity collision rejection;
- overlapping scope collapse;
- unavailable C2E linkage;
- prohibited excluded-rule request.

### C25-WP3 — Full-population shadow evaluator

Run the four draft contracts across the accepted population. Outputs are `SHADOW_ONLY`, `NON_CANONICAL` and `NON_PROMOTABLE`.

Report:

- event-record candidate counts;
- independent centre-time occurrences;
- overlap-component concentration;
- repeated-start suppression;
- first-valid latency;
- censoring and not-evaluable rates;
- criterion-level pass/fail records;
- exact reproduction and source accounting.

### C25-WP4 — Overlap, independence and episode-link audit

Apply strict, primary and permissive overlap variants. For each rule, report:

- component counts and maximum component size;
- stable versus sensitivity-dependent starts;
- episode-start, within-episode and episode-unavailable classifications;
- cross-rule co-occurrence;
- whether evidence supports an independent event-start interpretation.

No criterion may use a hidden composite score.

### C25-WP5 — Read-only review surface

Add a local read-only route showing:

- the full contract criteria;
- exact evidence results;
- occurrence lineage and source IDs;
- not-evaluable reasons;
- overlap and episode sensitivity;
- exclusions and authority boundaries.

The surface may not accept, name, promote, annotate or mutate events.

### C25-WP6 — Per-rule decision gate

Produce one consolidated packet with four independent sub-decisions, one per bounded rule. Each sub-decision allows PASS, DEFER, BLOCK, QUARANTINE or SUPERSEDE.

**Gate `C25-G6`: OPERATOR_REQUIRED.** A rule-level PASS may authorise preparation of a separate activation or release plan for that rule only. It does not activate or promote the rule directly. The operator may pass one rule and defer or block another.

## 11. Acceptance conditions

Minimum acceptance:

- exact reproduction of MTA-WP5 rule counts;
- zero formula or threshold drift;
- deterministic first-valid identities;
- explicit not-evaluable reasons;
- duplicate-start suppression is deterministic;
- all three overlap variants reported;
- no excluded rule appears in any draft contract;
- no hidden readiness badge or composite score;
- C2E linkage fails closed;
- focused tests and complete repository suite pass;
- no semantic, candidate, predictive or activation fields.

## 12. QA and automatic continuation

After `C25-G0`, non-reserved design, fixture, shadow and read-only packets may auto-ratify when tests pass, QA recommends PASS and no authority escape or unresolved warning exists. Stop at any event promotion, activation, formula/threshold change or new rule.

## 13. Stop conditions

Stop for:

- adding or reclassifying a rule;
- formula, threshold, clock, reset or source-population change;
- event promotion or activation;
- semantic naming, outcome joining or candidate authority;
- C2E dependency not lawfully available;
- non-reproducible evidence;
- capacity exceeded;
- Validation, R2, probability, risk, exposure or execution.

## 14. Rollback

Disable or supersede draft contracts and shadow routes while preserving source identities, evidence counts, reason distributions, QA, decisions and negative findings. No accepted record is deleted and no history is rewritten.

## 15. Work after `C25-G0` approval

Reconstruct the four rule evidence profiles, materialize draft contracts, run full-population shadows, complete overlap/episode-link audits, attach the read-only review surface, generate QA and stop at the four-part `C25-G6` operator gate.

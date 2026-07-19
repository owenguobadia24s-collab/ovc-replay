# OVC ABCD Operating Language Seed v0.1

**Status:** OPERATOR DIRECTION RECORDED — FORMALIZATION COHORT SELECTED; NOT YET ACTIVE  
**Programme:** OVC successor definition  
**Scope:** `OPT-A` through `OPT-D` only  
**Initial market:** GBP/USD  
**Source basis:** operator-owned Notion `OVC v.0` material  
**Authority:** none until terms pass measurement, replay, and operator review

---

## 1. Purpose

This document extracts the useful operating language already present in [OVC v.0](https://app.notion.com/p/272d31aa31338041a1c4e57a92f1228a) and turns it into a controlled seed for the successor.

It does not copy the old vocabulary into production. It separates concepts, resolves naming collisions, identifies claims that require stronger data, and defines how a word can become computable and evidentially trustworthy inside Options A–D.

The immediate system boundary is:

| Option | Responsibility |
|---|---|
| `OPT-A` | Source-faithful observations, time, instrument, session identity, and provenance |
| `OPT-B` | Deterministic measurements and versioned operating-language classifications available at decision time |
| `OPT-C` | Neutral forward outcomes that cannot alter the earlier classification |
| `OPT-D` | Cases, cohorts, contrasts, studies, counterexamples, and replay proof |

`OPT-E` through `OPT-L` are reserved for later development and are not defined here. Autonomous execution is the intended final operating frame, but this lexicon grants no execution authority.

---

## 2. Namespace correction

OVC v.0 uses the same letters for different ideas. The successor must never persist a bare letter.

| Namespace | Meaning | Example |
|---|---|---|
| `OPT-*` | Architectural responsibility | `OPT-B` measurement/language |
| `STORY-*` | Price-story phase | `STORY-B` expansion |
| `TPO-*` | Session-linked 2H time block | `TPO-C` London impulse block |
| `FUNC-*` | Behavioural function family or variant | `FUNC-EXPANSION` |
| `LB-*` | Liquidity-behaviour hypothesis | `LB-1` sweep |
| `ED-*` | Energy/rhythm hypothesis | `ED-4` compression |
| `POI-*` | Point/zone-of-interest type | `POI-FVG` |
| `DT-*` | Day-type classification | provisional until ID conflict is resolved |

The [Core Trader Loop](https://app.notion.com/p/242d31aa313380f4950fc4897c9393b6) defines twelve 2H blocks A–L and also uses AB/CD and ABCD aggregations at larger scales. Those are temporal groupings, not Options and not automatically price-story phases.

---

## 3. Core story grammar

The stable narrative spine extracted from OVC v.0 is:

```text
context
  -> location
  -> condition
  -> event
  -> response
  -> transition
  -> possible resolution
```

Every word in a daily story must occupy one of these grammatical roles and cite the measurements that support it. Narrative may summarize facts; it may not invent them.

### 3.1 Provisional story phases

The existing [Function Catalog](https://app.notion.com/p/255d31aa313380f6a65df8d694a7549b) examples imply this cycle:

| Story ID | Provisional meaning | Minimum distinguishing question |
|---|---|---|
| `STORY-A` | acceptance, consolidation, compression, or value building inside a declared container | Is price remaining inside a stable range without accepted displacement? |
| `STORY-B` | initiative expansion or repricing away from the prior container | Has price displaced and gained acceptance beyond prior structure? |
| `STORY-C` | retracement, correction, transition, or rebalancing within the active regime | Is movement corrective rather than a new accepted regime? |
| `STORY-D` | exhaustion, failed continuation, reversal, or control hand-off | Has prior direction failed and structure genuinely transitioned? |

These meanings are seeds, not final predicates. The source applies them fractally and sometimes combines phases within one period. A future classifier must therefore declare the instrument, scale, anchor range, and available-at timestamp.

### 3.2 Function families

The [Function Proofs](https://app.notion.com/p/25bd31aa313380e6b818e611191eb5c1) page supplies four useful behavioural families:

| Canonical seed | OVC v.0 family | Proposed relation |
|---|---|---|
| `FUNC-EXPANSION` | Expansion `1.x` | Usually supports `STORY-B` |
| `FUNC-RETRACEMENT` | Retracement `2.x` | Usually supports `STORY-C` |
| `FUNC-REVERSAL` | Reversal `3.x` | Usually supports `STORY-D` |
| `FUNC-CONSOLIDATION` | Consolidation `4.x` | Usually supports `STORY-A` |

“Usually” is deliberate. A function describes behaviour at a declared scale; a story phase describes its role in a declared sequence. They are related but not synonyms.

---

## 4. Required proof language

The five proof dimensions from [Function Proofs](https://app.notion.com/p/25bd31aa313380e6b818e611191eb5c1) should become explicit evidence fields:

| Proof dimension | ABCD treatment |
|---|---|
| Liquidity proof | `OPT-B` records measurable level interactions; unsupported intent claims remain hypotheses |
| Structural proof | `OPT-B` records breaks, reclaims, displacement, impulse/correction, acceptance/rejection |
| Profile/context proof | `OPT-B` records declared profile, range, location, session, and day context |
| Temporal proof | `OPT-B` records speed, duration, dwell, sequence, and tempo |
| Outcome proof | `OPT-C` records what followed; `OPT-D` evaluates it without retroactively changing the earlier tag |

No historical state may be relabelled because its outcome later became known. A corrected definition creates a new term version and triggers a fresh replay.

### 4.1 Structural seed terms

The following are retained as candidates, subject to exact formulas:

- break of structure (`BOS`);
- change of character (`CHoCH`);
- displacement;
- impulse and correction;
- acceptance and rejection;
- reclaim;
- range hold, range break, and range redefinition;
- higher high/lower low and higher low/lower high;
- dwell time, speed, duration, and follow-through;
- compression, expansion, exhaustion, transition, and rotation.

`BOS` and `CHoCH` must not remain chart-reader intuition. Their swing-selection method, close/wick rule, threshold, scale, confirmation delay, and first-valid timestamp must be declared.

---

## 5. Liquidity-behaviour seed

The [Liquidity Behaviour](https://app.notion.com/p/24dd31aa313380c68e24ccd3e01a1d35) catalog contributes eight useful behavioural hypotheses:

| ID | Seed name | Operational caution |
|---|---|---|
| `LB-1` | Sweep | Define the reference level, breach threshold, and observation window |
| `LB-2` | Reclaim | Define how quickly and how far price must return inside the level |
| `LB-3` | Stop cascade | “Stops” are inferred without execution/order data; classify observable acceleration first |
| `LB-4` | Void tap / imbalance test | Define the zone origin and whether a structure break occurred |
| `LB-5` | Internal liquidity grab | Define internal structure and prohibit intent claims without evidence |
| `LB-6` | Range sweep | Requires a pre-declared range and a measurable return inside |
| `LB-7` | Double sweep | Requires both declared boundaries to be breached before resolution |
| `LB-8` | Failed sweep | Define attempted breach, failure, follow-through window, and reset condition |

Useful sequence hypotheses such as `LB-1 -> LB-2` and `LB-7 -> LB-2` may enter research as preregistered sequences. They are not edges until `OPT-D` evidence demonstrates stable conditional value after costs.

---

## 6. Energy and rhythm seed

The [Energy Dynamics](https://app.notion.com/p/24dd31aa313380739de3ee88288f46d8) catalog supplies a compact rhythm vocabulary:

| ID | Seed name | Measurable starting point |
|---|---|---|
| `ED-1` | Absorption | Failed progress despite declared activity/volume; true passive absorption needs suitable market data |
| `ED-2` | Initiative flow | Directional displacement, range expansion, persistence, and accepted structure break |
| `ED-3` | Exhaustion | Declining progress, momentum, participation, or follow-through after an active leg |
| `ED-4` | Compression | Contracting range/volatility and reduced directional efficiency |
| `ED-5` | Imbalance surge | Sudden directional expansion relative to a declared baseline |
| `ED-6` | Chop/disorder | Low directional efficiency, high overlap, alternating returns, and wick-heavy motion |
| `ED-7` | Shift in flow | Measurable transition in directional control; order-flow claims require order-flow data |
| `ED-8` | Vacuum/void drift | Low-resistance price travel; an “empty order book” cannot be asserted from candles alone |

Candidate sequences such as `ED-4 -> ED-5` (compression to expansion) are suitable for Path 1 measurement and Path 2 story inspection. Names such as “absorption” and “vacuum” remain provisional unless the feed can support their causal meaning.

---

## 7. Location and POI seed

The [POI System](https://app.notion.com/p/254d31aa3133804eb6c9f52a51287396) contributes location types and interaction verbs.

### 7.1 Candidate location types

- positive/negative order block (`+OB`, `-OB`);
- fair-value gap or imbalance (`FVG`);
- equal highs/lows and liquidity pools (`EQH`, `EQL`);
- Initial Balance high/low (`IBH`, `IBL`);
- value-area high/low and point of control (`VAH`, `VAL`, `POC`);
- previous day/week/month high and low;
- midpoint/equilibrium;
- gap;
- range high, low, midpoint, and internal boundary.

### 7.2 Canonical interaction verbs

`approach`, `touch`, `breach`, `sweep`, `reclaim`, `accept`, `reject`, `hold`, `mitigate`, `fill`, `invert`, and `depart`.

Each verb needs a numeric predicate. “Respect” should be avoided in machine records unless decomposed into an observable interaction and response.

The source’s distinctions should be preserved: a sweep is not automatically a break; an FVG may behave as a magnet rather than a wall; and a POI is invalid without a declared origin rule.

---

## 8. Profile and day-type conflict

The [TPO Form](https://app.notion.com/p/24dd31aa3133800cbb0be414f6a6e6e2) page provides useful profile concepts, including D-shape, b-shape, P-shape, double distribution, tilted/inverted D, spike, transitional hybrid, and null/dead auction.

The [Market Profile](https://app.notion.com/p/24dd31aa3133801daa12e035afe86ad2) page contains two incompatible mappings for `DT-1` through `DT-6`. For example, one mapping assigns `DT-1` to Non-Trend and another assigns it to Trend. Therefore:

- no legacy `DT-*` numeric ID is canonical;
- names may be retained provisionally;
- numeric IDs must be replaced or remapped only after operator review;
- old records must preserve the source mapping/version they used.

Until resolved, use explicit names such as `DAY-TREND`, `DAY-NORMAL`, `DAY-NORMAL-VARIATION`, `DAY-NEUTRAL`, `DAY-DOUBLE-DISTRIBUTION`, and `DAY-NON-TREND` rather than `DT-1`–`DT-6`.

---

## 9. Mimic and false-function grammar

The [Function Composition Table](https://app.notion.com/p/248d31aa3133809ebca4d1d9a4f2b9d9) makes a crucial distinction: behaviour can resemble a higher-order function without achieving its structural result.

The successor should record two separate fields:

```yaml
behavioral_mimic: <what the sequence resembles>
structural_reality: <what was actually confirmed>
```

The source proposes at least two of three confirmations for a true higher-order function:

1. structural break (`BOS` or `CHoCH`);
2. clear displacement or momentum;
3. range redefinition.

This is a useful research rule, not yet a canonical threshold. `OPT-D` must test the combinations and preserve counterexamples before activation.

---

## 10. Term lifecycle

Every term passes through these states:

```text
IMPORTED
  -> NORMALIZED
  -> MEASURABLE
  -> REPLAY_VALIDATED
  -> OPERATOR_APPROVED
  -> ACTIVE
  -> DEPRECATED or WITHDRAWN
```

An active term requires:

| Field | Requirement |
|---|---|
| Identity | Stable ID, human name, version, and namespace |
| Meaning | Plain-language definition and forbidden interpretations |
| Inputs | Exact `OPT-A` observations and `OPT-B` measurements |
| Predicate | Deterministic formula, thresholds, parameters, null behaviour |
| Timing | First-valid timestamp and confirmation delay |
| Scope | Instrument, scale, session, regime, and range assumptions |
| Evidence | `OPT-D` examples, counterexamples, cohort result, and replay hash |
| Outcomes | Relevant `OPT-C` horizons, kept separate from classification |
| Governance | Author, reviewer, approval, activation, expiry, and replacement |

An LLM may retrieve, translate, summarize, cluster, and propose. It may not activate a term, change its predicate, or treat a persuasive narrative as proof.

### 10.1 Observable-name rule

The operator has directed that **all causal-sounding source terms** receive an observable operational name whenever the available feed cannot demonstrate the implied cause. The familiar OVC v.0 expression may remain as a searchable source alias, but it cannot be the canonical computed fact.

| OVC v.0 source expression | Candle-safe operational name | Additional evidence needed to restore the causal claim |
|---|---|---|
| Absorption | `FAILED_PROGRESS` or, when volume is available, `ACTIVITY_WITHOUT_PROGRESS` | Trades/quotes, volume-at-price, delta, or order-book evidence sufficient to show passive opposition |
| Initiative flow | `DIRECTIONAL_DISPLACEMENT` | Suitable transaction/order-flow evidence to attribute initiative aggression |
| Imbalance surge | `DIRECTIONAL_RANGE_SURGE` | Declared volume/delta evidence for an actual participation imbalance |
| Shift in flow | `DIRECTIONAL_CONTROL_TRANSITION` | Order-flow evidence showing a change in initiating/absorbing participants |
| Vacuum / void drift | `LOW_OVERLAP_DIRECTIONAL_DRIFT` | Order-book/depth evidence demonstrating missing liquidity |
| Stop cascade | `ACCELERATED_DIRECTIONAL_FLUSH` | Liquidation, transaction, or venue data demonstrating chained stop execution |
| Sweep | `REFERENCE_LEVEL_BREACH_AND_RESPONSE` | Stop/order evidence if the system wishes to claim that stops were cleared |
| Internal liquidity grab | `INTERNAL_LEVEL_BREACH_AND_RESPONSE` | Evidence supporting participant intent or liquidity-taking causation |
| Order block | `SOURCE_DEFINED_REACTION_ZONE` until formally specified | A declared construction rule; causal institutional-order claims need stronger market evidence |

This rule applies to future vocabulary as well: describe what the data shows first, then attach a causal interpretation only as a separately evidenced hypothesis.

---

## 11. First vertical slice

The first language-validation slice should use GBP/USD only:

1. `OPT-A`: ingest source-faithful 2H bars and 15M detail with provenance.
2. `OPT-B`: calculate range/location/structure measures and normalize a small initial vocabulary: compression, displacement, sweep, reclaim, acceptance, rejection, and transition.
3. `OPT-C`: record neutral 1h, 2h, 4h, 8h, 24h, and 48h path/outcome measures.
4. `OPT-D`: produce inspectable cases, counterexamples, matched contrasts, and replayable cohorts.
5. Compare `STORY-A`–`STORY-D` hypotheses with the measured sequence, without forcing every period into a phase.
6. Emit `UNCLASSIFIED` and `AMBIGUOUS` as valid results.

The exact provider symbol and session contract remain unresolved. Risk limits and abstention thresholds also remain unresolved. These uncertainties must be carried as explicit design dependencies, not filled by defaults.

---

## 12. Immediate Path 1 and Path 2 work

### Path 1 — numerical repetition

- formalize structural and rhythm measurements;
- find repeated 2H/15M sequences without outcome leakage;
- measure their neutral 1–48h outcome surfaces;
- retain negative and unstable findings.

### Path 2 — operating language

- retrieve examples and counterexamples for each source term;
- separate observable behaviour from inferred cause or intent;
- normalize synonyms and collisions;
- draft deterministic predicates;
- have the operator confirm whether the formal definition still expresses the intended market story.

Path 1 and Path 2 should meet in `OPT-D`: numbers challenge the language, and the language gives the numbers a testable question. Neither may silently overrule the other.

---

## 13. Operator decisions recorded

| Decision | Operator direction | Consequence |
|---|---|---|
| Story-phase logic | `STORY-A`–`STORY-D` accepted as the intended provisional phase model | Proceed to deterministic definitions and counterexample testing |
| First formalization cohort | All seven proposed terms selected | Formalize compression, displacement, sweep, reclaim, acceptance, rejection, and transition |
| Namespaces | `OPT-*`, `STORY-*`, `TPO-*`, and supporting namespaces accepted | Bare letters are prohibited in persisted records and interfaces |
| Causal terminology | Apply observable renaming to all unsupported causal terms | Source expressions remain aliases; canonical facts describe only what the feed proves |

### 13.1 Selected first cohort

| Candidate term | Initial observable question | Status |
|---|---|---|
| `COMPRESSION` | Has range/volatility contracted and overlap increased relative to a declared baseline? | SELECTED FOR FORMALIZATION |
| `DISPLACEMENT` | Has directional travel, close location, and range expansion exceeded declared baselines? | SELECTED FOR FORMALIZATION |
| `REFERENCE_LEVEL_BREACH_AND_RESPONSE` | Did price breach a pre-declared level, and what measurable response followed? | SELECTED; operational replacement for causal `SWEEP` |
| `RECLAIM` | Did price return through a breached level within a declared time/distance window and regain acceptance? | SELECTED FOR FORMALIZATION |
| `ACCEPTANCE` | Did price remain beyond/within a declared boundary for sufficient time, closes, or traded activity? | SELECTED FOR FORMALIZATION |
| `REJECTION` | Did price test or breach a boundary and depart without satisfying acceptance? | SELECTED FOR FORMALIZATION |
| `TRANSITION` | Did the measured state change from one valid condition to another under a declared state machine? | SELECTED FOR FORMALIZATION |

The familiar word `SWEEP` remains available to the operator as an interpretive alias. Computation and evidence use `REFERENCE_LEVEL_BREACH_AND_RESPONSE` unless a future feed supports the stronger liquidity-causation claim.

### 13.2 Decisions still open by design

Numerical risk limits and exact provider/session contracts remain open by operator choice. They must not be guessed during vocabulary formalization.

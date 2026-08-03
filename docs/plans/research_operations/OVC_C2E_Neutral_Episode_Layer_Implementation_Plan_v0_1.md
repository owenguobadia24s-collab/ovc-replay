# OVC C2E Neutral Episode Layer Implementation Plan v0.1

## 1. Identity and authority

- **Programme ID:** `OVC-C2E-NEUTRAL-EPISODE-v0.1`
- **Plan ID:** `OVC-C2E-NEUTRAL-EPISODE-IMPLEMENTATION-PLAN-0.1`
- **Source authority:** `MTA-G8-C2E=PASS`
- **Source decision:** `MTA-G8.OPERATOR.MULTIPART.20260803T114000+0100`
- **Initial gate:** `C2E-G0`
- **Current status:** `GATE_READY`
- **Authority available now:** preparation of this plan and its gate packet only
- **Authority denied now:** C2E implementation, activation, episode promotion, market meaning, candidate or family authority

`C2E-G0` is operator-required because C2E is a deferred capability. Plan preparation does not activate the layer.

## 2. Purpose

Design and, only after `C2E-G0`, implement a deterministic neutral episode layer that groups existing C2 states and transitions into event-relative structural intervals without assigning semantic names, predictive meaning, probability or trading significance.

The layer exists to answer:

- where a contiguous structural change begins and ends;
- which fixed-clock C2 states and transitions belong to the same neutral interval;
- how episode identities behave across `2H_A_L` boundaries and parent-context changes;
- how overlapping review windows collapse into independent or sensitivity-dependent occurrences;
- whether downstream C2.5 event contracts can reference stable episode identities without converting research-selection markers into market events.

The layer must preserve the distinction:

> Fixed clocks measure the market. Neutral episodes organise already-measured state change. They do not replace the clock and do not create meaning.

## 3. Binding baseline findings

The plan inherits:

- 7,116 eligible review windows;
- 1,779 exact centre-time occurrences after BID/ASK and local/parent collapse;
- 20 primary connected overlap components, with maximum size 166;
- 24 strict components and 18 permissive components;
- 1,456 occurrences classified `MATERIAL_SENSITIVITY`;
- 323 occurrences classified `STRUCTURALLY_UNSTABLE`;
- zero occurrences classified `ROBUST` across the three frozen overlap variants;
- 6,783 target C2 transitions and 8,598 target C2 states;
- no direct MTA/RO4 comparability conclusion because RO4-G6 evidence remains unavailable.

These findings require sensitivity-aware design. They do not establish that 20 market episodes exist.

## 4. Scope

### 4.1 Included

- GBPUSD, BID and ASK, 15M and existing `2H_A_L` context only;
- accepted C2 state and transition identities;
- deterministic episode start, continuation, termination and censoring records;
- event-relative sequence positions measured from a neutral episode start;
- links to fixed-clock identities and first-valid timestamps;
- the three frozen overlap variants from MTA-WP6;
- explicit cross-scale context changes without blending local and parent states;
- RO4 comparison adapters that preserve separate object identities;
- local read-only fixtures and console presentation;
- QA, gate packets, programme state and rollback.

### 4.2 Excluded

- semantic episode names, archetypes, pattern families or theories;
- predictive labels, outcomes, probability, risk, exposure or execution;
- selector replacement or candidate promotion;
- C2 formula, threshold, clock, continuity or reset changes;
- C2.5 event activation;
- merging MTA clusters with RO4 recurrence candidates;
- Validation consumption, R2 publication or new immutable releases;
- new instruments, markets, sides, providers or dependencies.

## 5. Neutral episode object

A neutral episode record must contain at minimum:

- `episode_id` derived deterministically from the frozen source identity and boundary records;
- `source_release_id`, instrument, side and scope;
- `start_transition_id` and start first-valid timestamp;
- ordered C2 state and transition IDs;
- fixed-clock membership for every member;
- parent identity, parent age and parent-change flags;
- termination classification;
- censoring status and reason;
- overlap-variant membership under strict, primary and permissive rules;
- sensitivity classification;
- source hashes and algorithm version;
- authority labels `NEUTRAL`, `NON_SEMANTIC`, `NON_PREDICTIVE`, `NON_PROMOTABLE`.

An episode is not a pattern, candidate, event contract or market regime.

## 6. Boundary model

`C2E-G0` must freeze a deterministic boundary contract using only accepted C2 transitions and evaluability states.

Permitted boundary inputs:

- transition first-valid timestamps;
- axis value changes and evaluated/not-evaluated status;
- reset and censoring records;
- parent identity changes;
- fixed source discontinuities;
- the four MTA-supported marker rules as trace references only, not boundary authority.

Prohibited boundary inputs:

- future price path;
- outcomes or returns;
- operator labels;
- semantic names;
- adjustable post-hoc thresholds;
- cluster membership chosen to improve apparent coherence.

The primary boundary rule must be preregistered. Strict and permissive sensitivity variants must be reported but may not silently replace it.

## 7. Performance and artifact contract

Each packet is bounded to four hours local runtime and 10GB external artifact size. Long scans checkpoint every 30 minutes. `CAPACITY_EXCEEDED` preserves completed partitions, manifests and hashes, marks the packet blocked and prevents silent sampling or threshold weakening.

No raw market data, caches or large derived episode populations are committed to Git.

## 8. Work packets

### C2E-00 — Contract and authority freeze

Deliver:

- neutral episode contract;
- episode schema and lifecycle registry;
- primary, strict and permissive boundary variants;
- source and identity contract;
- MTA/RO4 integration contract;
- performance contract;
- `C2E-G0` operator packet.

**Gate `C2E-G0`: OPERATOR_REQUIRED.** PASS authorises bounded implementation and shadow generation only. It does not activate C2E.

### C2E-WP1 — Deterministic episode builder

Implement a fail-closed builder that:

- consumes accepted C2 state/transition records only;
- orders by first-valid time;
- never consumes future state;
- creates deterministic IDs;
- records resets and missing evidence as censoring rather than inferred continuity;
- emits no semantic or candidate fields.

Fixtures must cover normal continuation, parent changes, clock-boundary crossing, reset censoring, missing axes, BID/ASK pairing and identity collision rejection.

### C2E-WP2 — Full-population shadow build

Build neutral episodes over the accepted June population. Report:

- all state and transition accounting;
- episode counts by side, scope, week and A–L block;
- duration and membership distributions;
- censored and not-evaluable episodes;
- boundary cause counts;
- parent changes within episodes;
- exact reconstruction and rerun equality.

Outputs remain `SHADOW_ONLY`, `NON_CANONICAL` and `NON_PROMOTABLE`.

### C2E-WP3 — Overlap and independence sensitivity

Map all episode records to strict, primary and permissive MTA overlap variants. Report:

- component membership;
- episode fragmentation and fusion across variants;
- stable boundary counts;
- sensitivity classification;
- effective independent occurrence estimates with explicit method;
- concentration by time, week, side and scope.

No episode may be called robust unless it passes a preregistered robustness contract approved at `C2E-G0`.

### C2E-WP4 — RO4 integration and contradiction audit

RO4 sequence windows, recurrence candidates and friction records remain separate analytical objects.

The adapter may create cross-references only. It may not:

- convert an RO4 candidate into a C2E episode;
- annotate a C2E episode as an RO4 friction record;
- infer agreement while RO4-G6 remains blocked;
- use RO4 evidence as sufficient activation evidence.

Contradictions are recorded as `CROSS_PROGRAMME_INCONSISTENCY` incidents requiring operator review.

### C2E-WP5 — Read-only review surface

Add a local read-only route within the existing Research workspace. It may display:

- episode identity and source lineage;
- ordered state/transition members;
- fixed-clock and parent-context changes;
- censoring and sensitivity status;
- MTA and RO4 cross-references.

It may not support naming, annotation, acceptance, promotion or write actions.

### C2E-WP6 — Final evidence and activation gate

Produce a consolidated evidence packet with:

- exact population accounting;
- QA;
- sensitivity and contradiction incidents;
- authority delta;
- rollback;
- recommendation among PASS, DEFER, BLOCK, QUARANTINE or SUPERSEDE.

**Gate `C2E-G6`: OPERATOR_REQUIRED.** A PASS may authorise a separately identified C2E activation or release plan. It does not activate C2E directly.

## 9. Acceptance conditions

Minimum acceptance:

- zero unaccounted C2 states or transitions;
- zero future-information use;
- deterministic IDs and rerun equality;
- all censoring explicit;
- all three overlap variants reported;
- no semantic, candidate or predictive fields;
- RO4 separation preserved;
- no unresolved cross-programme contradiction hidden;
- focused tests and complete repository suite pass;
- local read-only route fails closed on identity or schema mismatch.

Material concentration or sensitivity is a finding, not a reason to alter the preregistered primary rule silently.

## 10. QA and gates

Non-reserved packets after `C2E-G0` may auto-ratify only when tests pass, QA recommends PASS, no unresolved warning remains and the authority delta remains shadow/read-only. Stop at any proposal to activate, publish, promote or assign meaning.

## 11. Stop conditions

Stop for:

- C2E activation or release identity;
- semantic names or pattern families;
- candidate or selector promotion;
- new boundary threshold not frozen at `C2E-G0`;
- clock, reset or formula change;
- outcome joining;
- Validation, R2, probability, risk, exposure or execution;
- non-reproducible evidence or capacity exceeded.

## 12. Rollback

Disable or supersede the derived episode route and preserve all accepted source identities, episode manifests, QA, gate decisions, contradictions and negative evidence. Never delete accepted records or rewrite history.

## 13. Work after `C2E-G0` approval

Implement the neutral episode contract and deterministic builder, produce the full-population shadow, run three-variant sensitivity and RO4 contradiction audits, attach the local read-only presentation, complete QA and stop at `C2E-G6`.

# Pattern Discovery Transition and Candidate-Window Engine Contract v0.1

## Purpose

This contract governs `PD-WP1`. It permits deterministic extraction of first-valid C2 transitions, append-only persistence of derived TriggerEvents and deterministic creation and lifecycle management of CandidateWindows on synthetic fixtures and approved read-only C2 inputs.

It grants no live prospective-processing authority, no trigger-definition activation, no novelty, clustering, evidence-write, selector, release, R2, C2E, C2.5, C3, Validation, probability, exposure, trading, execution or agent-write authority.

## Admissible source profile

Each C2 snapshot must bind:

- one exact C2 state ID;
- one exact C2 release and manifest;
- `15M` or `2H_A_L`;
- `BID` or `ASK`;
- one evaluation scope and parameter pack;
- one selector identity;
- all five axes: `LOCATION`, `MOTION`, `ORGANISATION`, `INTERACTION`, `QUALITY`;
- relation-set identity and explicit level/container references;
- first-valid UTC chronology.

Transition extraction rejects mixed releases, manifests, clocks, price sides, scopes, parameter packs or selectors. The current state must be strictly later than the previous state.

## TransitionRecord

The extractor compares each full axis payload, including status, value, reason and measurement. It also compares relation-set, level-set, container-set, parent-container and boundary/relation identities. One changed domain produces one TransitionRecord.

Transition identity is a SHA-256-derived stable ID over:

- exact before/after source references;
- first-valid time;
- clock, side and scope;
- changed domain and before/after values;
- extractor version.

The same sources and extractor version must produce byte-equivalent records independent of local path, machine and run time.

## TriggerEvent persistence

`PD-WP1` does not decide whether a trigger predicate is true. It accepts a declared trigger request produced by fixtures or a later authorised trigger engine, binds it to one or more existing TransitionRecords and creates a deterministic TriggerEvent.

Every TriggerEvent is retained in an append-only derived JSONL ledger. Duplicate IDs are rejected. Trigger precedence changes display-primary selection only; it never deletes or overwrites an event.

## Candidate deduplication

The canonical key is:

`instrument | price_side | clock | evaluation_scope | primary_trigger_family | parent_container_id | boundary_or_relation_id | open_window_epoch`

A compatible TriggerEvent attaches to the existing open candidate. An incompatible closure profile receives a separate candidate identity and remains subject to the frozen caps.

Initial caps:

- one open candidate per trigger family, instrument, clock, side and scope;
- twenty simultaneously open candidates per instrument.

Suppressed candidates remain persisted with `SUPPRESSED_QUEUE_CAP` and an exact reason. No trigger or candidate is silently deleted.

## Trigger snapshot

The trigger snapshot hash contains only information available at the trigger first-valid time: exact C2 source binding, axes, structural references, trigger event and trigger family. Later accumulation must never alter this hash.

## Candidate lifecycle

Normal lifecycle:

`OPEN -> ACCUMULATING -> READY_FOR_REVIEW`

Additional fail-closed transitions:

- temporary intact delay: `OPEN/ACCUMULATING -> OPEN_PENDING_INPUT -> ACCUMULATING` after validated catch-up;
- missing source interval: `OPEN/ACCUMULATING -> READY_FOR_REVIEW` with `CENSORED_GAP`;
- parent-container replacement: `OPEN/ACCUMULATING -> READY_FOR_REVIEW` with `CENSORED_CONTEXT_CHANGE`;
- maximum duration: `OPEN/ACCUMULATING -> READY_FOR_REVIEW` with `CENSORED_MAX_DURATION`;
- quarantined source: `OPEN/ACCUMULATING -> INVALID` with `INVALID_SOURCE_QUARANTINED`;
- selector or release change: stop source binding and invalidate open windows with `SOURCE_SELECTOR_CHANGED` pending a new operator rebind.

Terminal objects are not edited into a different interpretation. Later corrections create new linked records in later authorised packets.

## Persistence boundary

TransitionRecord and TriggerEvent JSONL files are replaceable derived artifacts. CandidateWindows are derived runtime/read-model objects. None becomes canonical evidence. No code in this packet may write the C2 prospective evidence ledger.

## Deterministic acceptance

`PD-G1` may pass only if:

1. repeated extraction produces identical transition identities and ordering;
2. chronology and source rebind attempts fail closed;
3. every trigger event is append-only and duplicate-safe;
4. compatible duplicates attach rather than open a second window;
5. incompatible closures remain separate subject to caps;
6. cap suppression is explicit and auditable;
7. trigger snapshots remain unchanged after later accumulation;
8. gap, quarantine, pending-input, context-change and selector-change paths match the failure matrix;
9. candidate outputs contain no outcome, probability, trade or execution fields;
10. focused and canonical repository tests pass.

## Rollback

Delete and rebuild derived TransitionRecord, TriggerEvent and CandidateWindow artifacts from approved sources. Preserve the PD-WP1 contract, QA packet and decision history. No market release, selector, evidence record or R2 object requires reversal.

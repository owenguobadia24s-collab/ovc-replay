# C2 Prospective Evidence Accumulation Contract v0.2

## Purpose

This contract governs append-only research records under `RESEARCH.OPT-B.C2.GBPUSD.DISCOVERY.v1` after C2-G7 accepted bounded prospective evidence accumulation. It supersedes v0.1 for new records; v0.1 remains an immutable historical contract.

## Authority boundary

The only active research selector is the exact remote-verified C2 Discovery release `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`. The Development release is reference-only. Validation remains `LOCKED_UNCONSUMED`.

WP7 authorises governed append-only research records only. It does not authorise selector changes, release mutation, R2 mutation, threshold changes, probability claims, exposure decisions, trading or execution.

## Time model

Every new record must declare:

- `market_window_start_utc`: inclusive start of the market interval reviewed;
- `market_window_end_utc`: end of the market interval reviewed and strictly later than the start;
- `trigger_first_valid_at`: first instant at which the referenced C2 trigger or state became valid, within the declared market window;
- `review_created_at_utc`: system time at which the review record was created, not earlier than the market-window end;
- `operation_mode`: the chronology and evidentiary treatment applied to the record.

The four timestamps must be timezone-aware UTC values. `trigger_first_valid_at` may equal either market-window boundary. `review_created_at_utc` must be strictly after C2-G7 acceptance.

## Operation modes

### `LIVE_PROSPECTIVE`

The market window and trigger occur after C2-G6 opened the research line, and the review is created through the governed operation without future-data access. Only this mode increments prospective-evidence counts and may support a future prospective C2E escalation packet.

### `TIME_GATED_REPLAY`

The operator reviews an earlier market window under an enforced admissible cutoff that prevents later data from entering the review. The record may be used for replay-method QA, interface testing and bounded comparative review, but it does not increment prospective-evidence counts and cannot satisfy the first-real-prospective-batch gate.

### `NON_EVIDENTIARY_REPLAY`

The operator reviews historical material without claiming time-gated evidentiary status. The record is context, training or workflow evidence only. It never increments evidence counts, cannot carry sequence-boundary-friction escalation weight and cannot support promotion.

Historical material must use one of the replay modes. It must never be relabelled as `LIVE_PROSPECTIVE`.

## Admissible record classes

- `STATE_FIDELITY_REVIEW`
- `BOUNDARY_CONFLICT_CASE`
- `ANOMALY`
- `INCIDENT`
- `BOUNDED_RESEARCH_QUESTION`

Each record must bind the research line, exact active release and manifest, canonical clock, price side, market window, first-valid trigger time, source-object identity, deterministic record ID, author, review creation time, operation mode and evidence status.

## Deterministic identity

The record ID is derived from the research line, record class, canonical clock, price side, operation mode, market-window boundaries, first-valid trigger time and sorted source-object IDs. Review creation time is excluded so that retrying a write cannot create a second identity for the same governed observation.

## Evidence status

New records begin as `OBSERVED_UNREVIEWED`. Permitted later states are `REVIEWED_ACCEPTED`, `REVIEWED_REJECTED`, `DUPLICATE_SUPERSEDED` and `INCIDENT_BLOCKED`. Status transitions must be append-only; prior rows are never rewritten.

## Prohibited seed material

The old 202-story programme, old 58-candidate programme, B-STATE-0.3b cases or labels, C2E episodes, C2.5 events, C3 meanings and historical OPT-C/OPT-D outputs cannot seed or count as WP7 prospective evidence.

## Fail-closed rules

Unknown record classes or modes, old v0.1 timestamp fields, missing lineage, reversed windows, a trigger outside its market window, a review created before window completion, pre-cutoff `LIVE_PROSPECTIVE` material, Validation references, prohibited imports, duplicate active record IDs, unresolved selector identity or any trading/execution authority cause rejection.

## Version transition

The accepted ledger contained zero real records when v0.2 was introduced. No record migration, timestamp inference or identity rewrite is authorised. New writes use v0.2. Any future v0.1 row is historical-only and cannot enter the active ledger.

## C2E escalation

Only repeated, reproducible and independently reviewed `LIVE_PROSPECTIVE` sequence-boundary-friction records may support a separate C2E proposal. This contract grants no C2E authority.

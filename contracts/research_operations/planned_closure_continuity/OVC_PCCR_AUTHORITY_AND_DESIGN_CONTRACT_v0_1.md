# OVC PCCR Authority and Design Contract v0.1

## Current authority

Only plan, schema, fixture, QA and gate preparation is active under `CCR-G5.OPERATOR.PASS.20260803T194600+0100`. Calendar materialisation, continuity code and shadow execution require `PCCR-G0=PASS`.

## Frozen baseline

- Clock: `2H_A_L_UTC`, unchanged.
- Continuity: strict fail-closed resets, authoritative.
- Provider gaps: strict resets, never closure-remediated.
- Instrument: GBPUSD only.
- Sides: existing BID and ASK only.
- Scope: accepted June evidence only.

## Permitted post-G0 objects

1. Versioned OVC-owned scheduled-closure calendar records.
2. Deterministic closure-classification records.
3. Closure-aware analytical-lineage tokens.
4. V0/V1 shadow comparison records.
5. Read-only audit projections.

Every derived record is `SHADOW_ONLY`, `NON_CANONICAL`, `NON_PROMOTABLE` and `NO_ACTIVATION`.

## Fail-closed rules

A closure-aware lineage is unavailable when calendar provenance is missing, a boundary is incomplete, the calendar was not first-valid in time, observed boundaries disagree, the discontinuity may be a provider gap, or any source identity is ambiguous. No fallback inference is allowed.

A lineage creates no bars, prices, state values or elapsed-observation count during closure. It becomes first-valid no earlier than the first completed post-open observation.

## Frozen views

- `V0_CURRENT_STRICT_CONTINUITY_AUTHORITATIVE`
- `V1_SCHEDULED_CLOSURE_LINEAGE_SHADOW_ONLY`

No third variant or parameter search is lawful.

## Permanent denials under this plan

No clock change, bar remapping, interpolation, synthetic data, provider-gap relaxation, C1/C2 formula or threshold change, selector/release mutation, semantic or candidate promotion, C2E/C2.5 resumption, Validation, publication, probability, risk, exposure or execution.

## Final boundary

`PCCR-G6` is operator-required. Its PASS may authorise a separate activation/release plan only; it cannot activate closure-aware continuity.

# OVC Population Allocation & Exposure Register Implementation Plan v0.1

Plan ID: `OVC-POPULATION-ALLOCATION-EXPOSURE-REGISTER-IMPLEMENTATION-PLAN-0.1`

Authority source: explicit operator instruction, 22 September 2026: “Implement a central OVC Population Allocation & Exposure Register.”

Baseline: `main@e6233e585d98f464bef6110d41b9fb8934cb2e9f`

Authority delta: NONE.

## Scope

Materialise a programme-agnostic append-only population/exposure register under Research Operations. Bind the curated Drive population bank without consuming protected outcomes or granting research-role authority. Provide contract, schema, deterministic implementation, seed registry, tests, QA, machine-readable state and rollback.

## Acceptance

- 32 instrument×partition identities and 64 paired 15M/120M clock views.
- Shared clock views resolve to one evidence group.
- Metadata-only access never manufactures Development eligibility.
- Substantive exposure forces Development reconciliation.
- Validation remains locked absent separate authority.
- Exposure events cannot grant authority or reference an unknown population.
- Historical bank labels never substitute for current exposure adjudication.
- Full repository assurance passes before integration.

## Successor

`POPREG-WP1-HISTORICAL-EXPOSURE-BACKFILL`: reconcile prior OVC studies into append-only exposure events without opening protected outcome payloads unnecessarily.

## Rollback

Forward revert/supersede while preserving population and exposure evidence. No deletion, history rewrite or freshness reset.

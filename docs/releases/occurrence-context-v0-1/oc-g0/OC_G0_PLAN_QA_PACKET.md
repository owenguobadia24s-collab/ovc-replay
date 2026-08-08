# OC-G0 — OccurrenceContext Implementation Plan QA Packet

**Plan:** `OVC-OCCURRENCE-CONTEXT-IMPLEMENTATION-PLAN-0.1`  
**Gate:** `OC-G0`  
**QA scope:** plan/design/authority/repository conformance  
**Baseline main:** `dd03abb71361c7111af64f9f71e8ea28a436a8f4`  
**Decision authority:** `OPERATOR_REQUIRED`  
**Authority effect of QA:** `NONE`

## QA recommendation

**PASS FOR OPERATOR RATIFICATION**, subject to exact final-head CI and review-thread clearance.

This QA recommends the implementation plan only. It grants no implementation authority.

## Conformance assertions

| ID | Assertion | Result |
|---|---|---|
| `OC-G0-QA-01` | Plan is downstream of merged `OC-D0 PASS` and does not reopen the accepted design. | PASS |
| `OC-G0-QA-02` | WP0-WP5 scope is bounded to repository engineering, read-only adapters, synthetic/fixture computation, tests and QA. | PASS |
| `OC-G0-QA-03` | C2/C2E structural history is immutable and no write/recompute route is authorized. | PASS |
| `OC-G0-QA-04` | `occurrence_key` remains structural-anchor-only and context cannot contaminate structural identity. | PASS |
| `OC-G0-QA-05` | `REPRESENTATION_INPUT` remains denied pending a separate RepresentationPack/governance path. | PASS |
| `OC-G0-QA-06` | MCARB scientific admission starts empty/inert; WP4 implements mechanics only. | PASS |
| `OC-G0-QA-07` | Market-condition scientific vocabulary starts empty/inert. | PASS |
| `OC-G0-QA-08` | C2E real-source replay remains `DENIED_DEFERRED_AT_C2E2_G6`; no route around the C2E operator DEFER exists. | PASS |
| `OC-G0-QA-09` | Validation occurrence/data access remains hard-denied. | PASS |
| `OC-G0-QA-10` | New instrument/market/side/clock/lattice is explicitly reserved. | PASS |
| `OC-G0-QA-11` | SFC remains deferred and is not a prerequisite for base OC implementation. | PASS |
| `OC-G0-QA-12` | C2P remains outside the implementation programme and cannot start after OC-G0 alone. | PASS |
| `OC-G0-QA-13` | C2.5/C3 semantic changes, selector/publication and promotion/exposure authority remain denied. | PASS |
| `OC-G0-QA-14` | WP0 fails closed on missing calendar/session/A-L semantics instead of inventing them. | PASS |
| `OC-G0-QA-15` | Intermediate gates are auto-ratifiable only while authority delta remains wholly non-reserved. | PASS |
| `OC-G0-QA-16` | Terminal `OC-G6` is operator-required before later C2P design may rely on the implementation as a frozen upstream contract. | PASS |
| `OC-G0-QA-17` | Rollback is forward-only/non-destructive and no force-push/history rewrite is permitted. | PASS |
| `OC-G0-QA-18` | Raw market streams, caches and large replay artifacts are excluded from Git. | PASS |

## Design-to-plan coverage

The plan includes explicit work for all accepted implementation-handoff areas:

- `OC-WP0` repository/source reconciliation;
- `OC-WP1` contracts/schema/role map/registries/fixtures;
- `OC-WP2` deterministic envelope builder/supersession/replay;
- `OC-WP3` C2/C2E/session/calendar/clock adapters;
- `OC-WP4` MCARB typed-reference extension surface;
- `OC-WP5` adversarial QA/read-only consumer integration;
- terminal `OC-G6` before C2P.

It also carries the accepted first-valid, no-mutation, missingness, field-role, Validation, MCARB and C2P identity firewalls into packet acceptance criteria.

## Deliberate deferrals

These are non-blocking because the plan explicitly forbids guessing or activating them:

- exact first calendar/session/A-L registry binding;
- real MCARB scientific admission;
- market-condition/regime taxonomy;
- future SFC reopening;
- future C2E real-source G6 supersession;
- future C2P programme.

If WP0 finds that an exact required semantic definition is absent rather than merely unmaterialized, the affected route must block at the operator boundary.

## Final-head requirements

Before presenting OC-G0 as decision-ready, the exact PR head must have:

- complete repository suite: `SUCCESS`;
- OVC FINAL_HEAD/profile assurance: `SUCCESS`;
- compatibility: `SUCCESS`;
- merge readiness: `SUCCESS`;
- unresolved blocking review threads: `NONE`;
- PR diff restricted to plan, gate, QA and machine-readable pre-ratification state artifacts.

## QA disposition

No design contradiction, hidden scientific activation, Validation leakage, C2P start or structural-history authority expansion is present in the plan as written.

**Recommended OC-G0 decision: `PASS`.**

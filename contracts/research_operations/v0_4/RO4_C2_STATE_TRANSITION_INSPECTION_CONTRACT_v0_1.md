# RO4 C2 State and Transition Inspection Contract v0.1

Status: `PROPOSED_AT_RO4_G0`

Plan: `OVC-RESEARCH-OPERATIONS-FOUNDATION-v0.4-C2-STATE-SEQUENCE-EVIDENCE-IMPLEMENTATION-PLAN-0.2`

## Inputs

Only exact source-bound C2 records from the active Discovery v2 selector or the declared Development v2 reference release are admissible. Each record must resolve release ID, manifest SHA-256, role, instrument, clock, side, source record identity, first-valid time, C1 parent and OPT-A source lineage.

## State index law

The five axes remain independent. `overall_state`, `winning_state`, hidden dominance and implicit neutrality are prohibited. Duplicate identities, unknown values and missing source objects block. State cardinality must reconcile by role, clock and side to the accepted source inventory.

## Transition index law

Every transition resolves exact source and target states; source precedes target; continuity and partition boundaries are explicit; simultaneous changed axes stay simultaneous; gaps, quarantine and unavailable parents terminate continuity. Canonical ordering is role, release, clock, side and source chronology.

## Access law

Discovery is allowed from the active exact selector. Development is bounded reference-only. Validation is denied before path or object resolution. Historical B-STATE is identity-only and cannot be indexed.

## Identity and determinism

Logical identity excludes machine paths, hostnames, worker IDs, run timestamps and UI order. Equivalent logical inputs produce byte-identical canonical JSON and identical logical hashes.

# OVC MTA Overlap and Independence Audit Contract v0.1

**Programme:** `OVC-MTA-v0.2`  
**Packet:** `MTA-WP6`  
**Gate:** `MTA-G6`

## Purpose

Collapse identical centre-time windows across BID/ASK and LOCAL/WITH_2H_PARENT scopes, then measure occurrence connected components under three frozen interval-graph variants: `STRICT_OVERLAP`, authoritative `PRIMARY_OVERLAP_PLUS_1`, and `PERMISSIVE_OVERLAP_PLUS_4`.

## Rules

The collapse key is the exact UTC centre time. Each occurrence retains every source window ID. Components are calculated over the nine-record window intervals. Strict requires interval overlap; primary permits a gap of one 15M interval; permissive permits a gap of four 15M intervals. Every occurrence belongs to exactly one component per variant.

Sensitivity is classified without semantic promotion. The audit may report `ROBUST`, `MATERIAL_SENSITIVITY` or `STRUCTURALLY_UNSTABLE`, but may not select a model, threshold, family or canonical overlap rule.

## Acceptance

MTA-G6 requires exact 7,116-window membership, exact collapse to 1,779 occurrences, exact three-variant component accounting, zero missing/duplicate membership, explicit sensitivity counts, checksum binding, focused/retained/complete/FINAL_HEAD assurance, QA PASS_WITH_MATERIAL_FINDINGS and no reserved authority delta.

## Rollback

Supersede through a new immutable checksum-bound audit version while preserving all variants, negative findings and decisions.

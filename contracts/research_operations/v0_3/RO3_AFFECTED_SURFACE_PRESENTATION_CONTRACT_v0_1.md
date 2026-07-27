# RO3 Affected-Surface Presentation Contract v0.1

Status: `FROZEN_AT_RO3_G0`

## Permanent authority banner

Every affected-surface projection must display:

> **DOWNSTREAM TRACE — READ ONLY. C2 AND PATTERN DISCOVERY AUTHORITY IS UNCHANGED.**

## Required separation

C1 fact explanation and downstream affected-surface trace are two visually and structurally distinct panels. A C1 null reason and a C2 transition must never appear together in one compact card, tooltip, table row, badge, score or summary sentence.

The C1 fact panel may contain exact arithmetic inputs, output, formula, unit, domain, null reason, first-valid time and source lineage.

The downstream trace panel may contain immutable child IDs, exact source binding, operation mode, cutoff, availability and trace status only.

## Prohibited presentation

Downstream counts or references may not be labelled, styled or sorted as defect, severity, confidence, tuning, remediation, fix priority, candidate quality or recommended action. No recompute, tune, mutate, promote, activate or write control is permitted.

Missing child references remain explicit as `TRACE_NOT_AVAILABLE`; they do not imply no effect.

## Technical enforcement

Projection schemas use separate object types and separate panel identifiers. Adapters reject mixed compact-card payloads and any write-capable field. Live route consumption stays disabled until operator-owned RC-G4.

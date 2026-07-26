# OVC Research Operations Foundation v0.2 authority contract

Document ID: `OVC-RO2-AUTHORITY-CONTRACT-0.1`
Status: `FROZEN_DESIGN_ONLY`
Gate: `RO2-G0`
Parent authority: `OVC-RESEARCH-OPERATIONS-FOUNDATION.v0.1 / RO-G3 PASS`

## Purpose

Define the exact authority boundary for Research Operations Foundation v0.2 before any runtime implementation begins. RO2 extends the accepted local Research Operations foundation with read-oriented workspace, observation, quality, lineage, replay, release-comparison and Console v0.3 projection contracts. It is not another market Option and does not alter OPT-A or OPT-B authority.

## Admitted capability

RO2-G0 admits design records and no-mutation validators for:

- role-workspace indexing;
- observation indexing;
- data-quality and bar-lineage inspection;
- admissible-cutoff replay design;
- release and workspace comparison;
- Research Console v0.3 read projections.

No runtime indexer, replay service, artifact resolver, adapter or UI action is authorised by RO2-G0.

## Read authority

- Discovery: metadata and content reads may be proposed for later implementation.
- Development: metadata and content reads may be proposed for later implementation.
- Validation: approved release identity, aggregate inventory and manifest identity only.
- Validation rows, bars, model outputs, path data, cases and derived records remain inaccessible.
- Validation denial occurs before path resolution, download, deserialisation, row filtering or cache lookup.
- C1 and C2 attachments are optional, exact-release-bound and read-only. Absence produces `NOT_AVAILABLE` or `NOT_EVALUABLE`.

## Write authority

Permitted at RO2-G0:

- branch-local contracts, registries, catalogues, fixtures, validators, gate packets and status reconciliation records.

Denied:

- runtime research-record creation by new v0.2 code;
- mutation of OPT-A, C1 or C2 records;
- Git primary-branch writes from any RO2 component;
- R2 writes, uploads, deletes or key changes;
- release freeze, publication, supersession or selector changes;
- parameter or threshold writes;
- C2 candidate construction, publication, selector or activation;
- probability, exposure, trading or execution objects;
- autonomous-agent authority.

The existing v0.1 append-only research-record service remains the only approved local record-freeze path.

## Dependency rule

```text
OPT-A sealed observations
  -> RO2 typed references and derived read projections
  -> Research Console v0.3 presentation
  -> optional call to the existing v0.1 append-only record service
```

QA is orthogonal and may `PASS`, `WARN`, `BLOCK` or `QUARANTINE`; it may not repair or reinterpret market records. Reverse writes and downstream-to-upstream reads are denied.

## Current-state basis

RO2-G0 is pinned to merged commit `85d2638d36c5039c35d2d49fcdb499dd48e7b354`, where C2-G4 completed exact-parent Discovery and Development replay with 404,434 state records and 323,910 transition records. Validation remained `LOCKED_UNCONSUMED`; C2 candidate, publication, selector and activation remained `NONE`.

## Exit authority

`RO2-G0 PASS_DESIGN_FREEZE` grants design-canon status only. RO2-WP1 runtime implementation remains `NOT_STARTED` and requires a separate operator instruction.

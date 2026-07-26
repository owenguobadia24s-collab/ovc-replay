# OPT-B.C1 v2 WP2 Operator Decision

## Decision

`PASS — CONTRACTS, FORMULAS AND SCHEMAS FROZEN`

## Reviewed baseline

- Repository: `owenguobadia24s-collab/ovc-replay`
- Baseline: `3940f64a635f547a6bef6045bd3a8a27e386dcdd`
- WP1 decision: `PASS — CLEAN C1 BOUNDARY APPROVED`
- Upstream selector set: `SELECTOR.OPT-A.GBPUSD.ROLESET.v1`, unchanged
- Validation: `LOCKED_UNCONSUMED`

## Frozen design

WP2 freezes the C1 machine-readable design around one admissible closed OPT-A v2 bar per record.

The formula registry `C1.FORMULAS.v0.1` contains 18 exact Decimal definitions:

- 14 current-bar facts with zero lookback;
- four prior-close facts with one lawful immediate contiguous-bar dependency;
- no rolling window, threshold, semantic label, state, event, outcome or exposure field.

The canonical initial scope remains:

- `GBPUSD`;
- `15M` and `2H_A_L`;
- separate `BID` and `ASK` records;
- H1 identities control-only;
- no midpoint, spread or cross-side repair.

## Null and chronology decision

- Zero-range bars retain absolute geometry and `FLAT` direction while all range-divided fields are null with `ZERO_RANGE`.
- First-partition and gap-adjacent bars retain current-bar geometry; prior-close fields are null with exact reason codes.
- A prior close must match release, manifest, instrument, clock and side and must close exactly at the current open time.
- C1 never searches backward across a gap and never substitutes another clock or side.
- An inadmissible current source bar produces no C1 record.

## Schemas frozen

- C1 bar primitive record;
- C1 release descriptor;
- C1 release manifest;
- exact publication approval;
- SHADOW/active selector;
- supersession record.

The release and selector registries contain planned identities only. No C1 release or manifest exists and every C1 selector remains `NONE`.

## QA decision

The C1 QA registry freezes ten blocking families covering arithmetic, domains/nulls, chronology, leakage, lineage, determinism, symmetry, serialization/identity, cardinality and authority boundaries. QA may block or quarantine but cannot repair or rewrite source facts.

Eight synthetic handoff fixtures cover valid 15M and 2H inputs, zero range, missing prior, gap adjacency, legacy parent rejection, control-clock rejection, side mismatch and current-source quarantine. They have no market authority, release-parent eligibility or discovery-seed eligibility.

## Authority delta

WP3 may implement and test:

- the exact OPT-A v2 handoff adapter;
- the Decimal formula engine;
- contiguous-prior resolution;
- deterministic record identity;
- canonical serialization;
- local validation on synthetic/golden fixtures.

The following remain denied:

- actual C1 market replay;
- local C1 release freeze;
- R2 publication;
- C1 selector activation;
- Validation consumption;
- C2 consumption;
- probability, exposure, trading and execution.

## Rollback

Rollback removes the WP2 freeze and WP3 build authority while preserving the WP1 boundary. It does not alter the active OPT-A selector set, remote objects or historical records and cannot reactivate legacy OPT-A or OPT-B.

## Next work packet

`OPT-B.C1 v2 WP3 — reference engine and fixture trust`

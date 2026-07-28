# PD-G5P — Correction Return Operator Decision

- **Gate:** `PD-G5P`
- **Iteration:** `2`
- **Plan:** `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1` v0.1
- **Operator command:** `OVC APPROVE PD-G5P PASS`
- **Decision:** `PASS`
- **Decision authority:** `OPERATOR`
- **Decided on:** `2026-07-28`
- **Reviewed gate head:** `2510dbf66794db7fc98476eb253863d8721088d8`
- **Reviewed authority source:** `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1`

## Accepted finding

The operator accepts the correction-return finding that all six PD-G5P correction objectives are closed, the v0.2 review workflow fails closed, the Console correction is read-only, the original signed pilot evidence is preserved and a second replay was not required under the reviewed C2 v1 gate state.

## Post-review authority conflict

Before this decision could be materialised, lawful `main` advanced to `0c687101e031b404b3994c8bb96d65b177f97743` under the separately operator-approved C1C-G4/G5 transaction. That transaction:

- activated `OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2` and selector `SELECTOR.OPT-B.C2.GBPUSD.v2`;
- superseded pilot namespace `PD.PILOT.GBPUSD.20260622_20260625.v1` as noncanonical lineage;
- created blocker `C1C-G5-BLOCK-001`;
- requires one operator-local, signed corrective pilot rerun in namespace `PD.PILOT.GBPUSD.20260622_20260625.v2` before the corrective programme can close.

The reviewed PD-G5P PASS delta names C2 v1 exactly. Applying it after the C2 v2 selector transaction would either bind canonical Discovery to a superseded source or silently substitute C2 v2. The first action conflicts with current authority; the second is an unapproved source and selector change. Neither is lawful.

## Decision effect

The operator PASS instruction is recorded, but its reviewed authority delta is **not effective**. No contract activation, identity-reset activation, `PD-WP5-CANONICAL` packet, canonical Discovery run or canonical append is authorised by this record.

Current authority remains fail-closed:

- canonical Discovery processing: `DENIED`;
- canonical append: `DENIED`;
- semantic, family, candidate, threshold, model and novelty promotion: `DENIED` or `NONE`;
- selector, release and R2 mutation: `DENIED`;
- Validation consumption: `LOCKED_UNCONSUMED`;
- probability, risk, exposure, trading, execution and agent write: `NONE`.

## Blocker and smallest lawful resolution

Blocker: `C1C-G5-BLOCK-001`.

1. Pull clean `main` containing `0c687101e031b404b3994c8bb96d65b177f97743`.
2. Run `./scripts/run_c1c_g5_pilot_corrective_rerun.ps1 preflight` locally.
3. Execute and finalize the approved C2 v2 corrective pilot with the exact local source root and private Ed25519 key.
4. Return the required compact signed files.
5. Reconcile PD-G5P through a superseding C2 v2-bound gate. Changing the exact source from v1 to v2 requires a new explicit operator decision.

## Rollback

Preserve this operator instruction, the reviewed gate packet, CORR1 evidence and all pilot artifacts. Keep the C2 v2 selector transaction effective, keep the original pilot superseded and keep every canonical or promotional authority denied until a superseding lawful gate is approved.

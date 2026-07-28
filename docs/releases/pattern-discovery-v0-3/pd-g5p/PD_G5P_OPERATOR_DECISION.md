# PD-G5P — Operator Decision

- **Gate:** `PD-G5P`
- **Gate title:** `Pilot Discovery Operations Acceptance`
- **Plan:** `OVC-C2-REAL-PROSPECTIVE-SOURCE-PD-WP5-ENABLEMENT-PLAN-0.1`
- **Plan version:** `0.1`
- **Original gate baseline:** `6c0aa91a6c51a86d39994ef363f8e29bb924764b`
- **Latest lawful main reviewed:** `1142abd2010b92b33e56bccc23e05ccd8bed1320`
- **Gate branch:** `gate/pd-g5p-pilot-operations-review`
- **Decision-bearing candidate:** `b1bb92faaf300c8422581f33f75db96e0ab10a3d`
- **Final pre-decision gate head:** `ba6fc9a5351b5049bcfc608a1e7e7f09db654429`
- **Pull request:** `#124`
- **Operator command:** `OVC APPROVE PD-G5P DEFER`
- **Decision:** `DEFER`
- **Decision authority:** `OPERATOR`
- **Decided on:** `2026-07-28`

## Accepted finding

The operator accepts the PD-G5P evidence finding that the Pilot Discovery machine rehearsal, exact-byte evidence chain, Ed25519 signatures, deterministic rerun and operator-review capture are valid, while operational acceptance for canonical Discovery is incomplete.

The decision preserves the signed Pilot Discovery run:

- pilot run `PD.PILOT.RUN.0cc5a59ca751583f3e50091c`;
- pilot namespace `PD.PILOT.GBPUSD.20260622_20260625.v1`;
- source `RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1`;
- compute run `RPS.RUN.7aeb551335d766ee3bf503e6`;
- source binding `RPS.BINDING.32fb3003efa072916c11e907`;
- signed replay acceptance `RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48`;
- signing binding `RPS.SIGNING.50092c28981fef08f53a6cb5`;
- operator `OVC.OPERATOR.PRIMARY.LOCAL.V1`.

All pilot artifacts remain append-only operational evidence, `PILOT_ONLY`, `NON_PROMOTABLE` and excluded from canonical Discovery counts.

## Authority granted

This `DEFER` decision authorises one bounded, non-activating correction packet, `PD-WP5-CORR1`, to:

1. inspect the five non-accepted pilot review objects using preserved read-only evidence;
2. assign deterministic workflow-defect, UI-friction, defer-resolution and structural-rejection codes;
3. identify affected workflow and Research Console components;
4. record reproduction steps, required evidence fields and deterministic acceptance tests;
5. version the review-input, review-receipt, defect-ledger and evidence-presentation contracts;
6. implement fail-closed validation and read-only Console presentation corrections;
7. test the versioned corrections on governed fixtures and the preserved pilot projection;
8. freeze a proposed final PD-WP5 canonical Discovery contract and complete identity-reset procedure;
9. determine whether a second bounded correction replay is necessary;
10. return to `PD-G5P` with a closed correction ledger and consolidated operator packet.

The correction packet may be automatically ratified and squash-merged only while its authority delta remains wholly deterministic, non-activating and inside this scope.

## Authority not granted

This decision does **not** authorise:

- a second Pilot Discovery operation or correction replay;
- canonical 2021–2023 Discovery processing;
- inclusion of pilot outputs in canonical populations, family counts or evidence ledgers;
- reuse of pilot candidate, cluster, medoid, assignment, family or evidence identities;
- final family, semantic, archetype or theory promotion;
- threshold, queue-cap, distance-weight, clustering-model or candidate promotion;
- active novelty ranking;
- selector, release or R2 mutation;
- Validation consumption;
- LIVE_PROSPECTIVE relabelling or provider intake;
- probability, risk, exposure, trading, execution, autonomous processing or agent write.

A second replay, canonical Discovery release, identity activation or any promotional authority requires a new explicit operator decision.

## Required corrections

`PD-WP5-CORR1` must close these exact findings:

- `PDG5P-DEFECT-SPEC-001` — workflow defects cannot be accepted without a code, affected component, reproducible actual/expected behaviour and acceptance test;
- `PDG5P-UI-SPEC-001` — UI-friction findings cannot be accepted with an empty code list or without an affected Console surface and acceptance criterion;
- `PDG5P-DEFER-RESOLUTION-001` — deferred objects require a reason code, resolution criteria and next lawful review condition;
- `PDG5P-REJECTION-BASIS-001` — rejected objects require a structural, non-semantic rejection basis and evidence references;
- `PDG5P-CONTRACT-FREEZE-001` — a versioned final contract candidate and exact diff from the pilot contract must be frozen;
- `PDG5P-REPLAY-AUTHORITY-001` — the packet must recommend whether a replay is necessary, but may not execute one.

## Accepted tests and QA

- Decision-bearing PD-G5P workflow `30368743532`, job `90306722224`: `PASS`.
- Final evidence-only verification `30369171169`, job `90308171804`: `PASS`.
- Latest-main merge verification `30369976011`, job `90310962090`: `PASS`.
- QA result: `DEFER_VERSIONED_CORRECTION_REQUIRED`.
- Unresolved review threads: none.

## Rollback

Revert the gate decision and correction packet while preserving and sealing every signed pilot artifact. Restore `PD-G5P` to operator-decision-required state, keep `PD-G4B` approved and keep canonical Discovery, replay and promotional authority denied. No rollback may delete, rewrite or relabel pilot evidence.

## Continuation

1. Commit this operator decision and updated programme state.
2. Squash-merge PR `#124` into `main` after final checks pass.
3. Create `build/pd-wp5-corr1` from the resulting lawful main tip.
4. Execute the bounded correction-specification packet continuously.
5. Auto-ratify and merge deterministic non-activating correction work when eligible.
6. Stop at a consolidated operator gate only if a second replay or canonical Discovery authority is requested, or if the correction evidence cannot be closed inside scope.

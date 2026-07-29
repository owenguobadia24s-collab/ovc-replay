# C1C-G5-CORR3 Delegated Decision

## Decision

**PASS — implementation and QA only.**

The approved operator DEFER delegated authority for the bounded, nonactivating `C1C-G5-CORR3` packet. The packet remains wholly inside that envelope and is eligible for automatic ratification and squash merge.

This decision does **not** dispose the remaining pilot object and does **not** decide the return gate `C1C-G5-CORRECTIVE-PILOT-REVIEW`.

## Authority

- Programme: `OVC-C1-WICK-BALANCE-CORRECTIVE-PROGRAMME-0.1`
- Plan version: `0.1`
- Packet: `C1C-G5-CORR3`
- Operator source command: `OVC APPROVE C1C-G5-CORRECTIVE-PILOT-REVIEW DEFER`
- Baseline main: `41623d07e73b2e0b87824c365f11acca9e51d73d`
- Tested candidate head: `9a4fa3f3472d8c09981264c29093d13115a34bcb`
- PR: `#141`
- Decision authority: `DELEGATED_AUTO_EXECUTABLE`
- Authority delta: `NONACTIVATING_READ_ONLY_STRUCTURAL_COMPARISON_EXPOSURE_ONLY`

## Accepted implementation

The packet:

1. binds exactly `PDPILOT-CANDIDATE-bab63b935155e4d9033aed81`;
2. resolves the exact preserved assigned-medoid fingerprint;
3. verifies the frozen distance pack and rebuilt deterministic scale-pack identity;
4. exposes all six composite-distance domains, weights and weighted contributions;
5. proves the recomputed distance matches the preserved assignment and p90 outlier classification;
6. exposes exact-window, dedup-key and same-scope overlap status;
7. documents the existing `TR-PER-001 / LONG_PERSISTENCE` derivation without changing its rule;
8. preserves the CORR2 rejected object and four non-deferred structured-v2 decisions;
9. provides an operator-local, one-object, append-only prepare/finalize workflow;
10. keeps the Console projection read-only and separately bannered.

## Tests and QA

- Dedicated CORR3 workflow run `30415338772`, job `90460513735`: **PASS**.
- Generic repository workflow run `30415338842`, job `90460513953`: **PASS**.
- QA recommendation: `PASS_IMPLEMENTATION_MERGE_AND_REQUIRE_OPERATOR_LOCAL_REREVIEW`.
- Blocking implementation issues: none.

## Retained boundaries

No machine replay, provider intake, trigger rule, distance-pack, cluster, threshold or model change is authorised. Canonical Discovery processing and append remain denied. Semantic, family, candidate and novelty promotion remain absent. Selector and release mutation, R2 publication, Validation consumption, probability, risk, exposure, trading, execution and agent-write authority remain denied or none.

All outputs remain `PILOT_ONLY` and `NON_PROMOTABLE`.

## Rollback

Revert only CORR3 code, schemas, tests and repository court records through a new non-destructive commit. Preserve the immutable pilot run, all signed v1/v2/CORR2 evidence, operator-local CORR3 artifacts and every prior decision.

## Continuation

After squash merge, the only next lawful step is operator-local execution:

1. `preflight`;
2. `prepare`;
3. human review of the exact remaining candidate;
4. `finalize` with the existing operator Ed25519 key;
5. return the compact signed CORR3 closure artifacts to the same operator gate.

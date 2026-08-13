# SIQ-RUNTIME-G1 — Serialized Integration Queue Runtime Activation Readiness

**Programme:** `OVC-SERIALIZED-INTEGRATION-QUEUE-RUNTIME-v0.1`  
**Plan:** `OVC-SIQ-FINALISATION-PLAN-0.1`  
**Packet:** `SIQ-RUNTIME-WP1`  
**Gate:** `SIQ-RUNTIME-G1`  
**Gate class:** `OPERATOR_REQUIRED`  
**Recommended decision:** `PASS`  
**Current implementation authority:** `NONE_INACTIVE_RUNTIME_IMPLEMENTATION`  
**Proposed authority delta:** `ACTIVATE_SIQ_MINIMAL_CRITICAL_SECTION_AS_FINAL_INTEGRATION_RUNTIME`  
**Scientific / market / Validation / publication / probability / risk / exposure / execution authority delta:** `NONE`

## 1. Court-record identity

- Constitutional object: `OVC-SERIALIZED-INTEGRATION-QUEUE-v0.1`.
- Constitutional PR: `#762`.
- Constitutional squash merge: `a11d6acdb671eaef9e3cf58369d4aae0269f09bb`.
- Constitutional merge parent / prior lawful main: `2ba0d059de36dc6e60cc66a2d78923c92505ec88`.
- Runtime implementation baseline: `main@a11d6acdb671eaef9e3cf58369d4aae0269f09bb`.
- Runtime PR: `#769` — `SIQ-RUNTIME-WP1: inactive serialized integration queue runtime`.
- Runtime branch: `build/siq-runtime-v0-1-a11d6acd-r2`.
- Mechanically evaluated implementation candidate: `ab1916cbf57a12ab0837073698279d69e4d2836a`.
- GATE_READY programme-state materialisation commit: `8c5538e34492f7b1924b14c876bb9da5f6c5c132`.
- Current main at gate preparation: `a11d6acdb671eaef9e3cf58369d4aae0269f09bb`; no intervening main advance was observed during the mechanical assurance window.

## 2. Completed constitutional finalisation

PR #762 was re-resolved from the then-current repository court record rather than its stale original baseline. The branch was reconciled without force-push or history rewrite, exact-head repository/parity/profile/readiness assurance passed, delegated constitutional PASS was recorded, and PR #762 was squash-merged.

The merged constitution preserves:

- deterministic FIFO READY ordering by materialised `ready_sequence`, then `packet_id`, then pinned candidate SHA;
- one final-integration lease holder only;
- explicit `BASE_INDEPENDENT` versus `BASE_SENSITIVE` assurance;
- prohibition on BASE_INDEPENDENT lease ownership;
- PDC movement classification and selective assurance reuse;
- automatic lawful requeue preserving packet/write-set/semantic-owner identity;
- immediate successor advancement;
- `parallel_merge=false`;
- squash-only permanent integration;
- force-push/history rewrite prohibition;
- all existing operator-reserved authority boundaries.

The constitutional merge explicitly records that runtime activation is separate; the constitutional authority delta is only `DEVELOPMENT_ORCHESTRATION_CONSTITUTION_ONLY`.

## 3. Runtime materialised in SIQ-RUNTIME-WP1

The inactive runtime packet adds:

- `docs/plans/development/OVC_SIQ_FINALISATION_PLAN_v0_1.md`
- `contracts/development/v0_4/OVC_SERIALIZED_INTEGRATION_QUEUE_RUNTIME_CONTRACT_v0_1.md`
- `src/ovc/development/skills/siq_core.py`
- `src/ovc/development/skills/siq_reconciliation.py`
- `src/ovc/development/skills/siq_receipts.py`
- `schemas/development/serialized_integration_queue_state.schema.json`
- `tests/development/test_siq_queue.py`
- `tests/development/test_siq_controls.py`
- `tests/development/test_siq_reconciliation.py`
- `tests/development/test_siq_receipts.py`
- `tests/development/test_siq_pdc_contract.py`
- `docs/programmes/siq-runtime-v0-1/SIQ_RUNTIME_PROGRAMME_STATE.json`

The runtime implements deterministic candidate admission, materialised ready sequence, READY queue/head selection, a single logical lease holder, assurance classification, timeout/release/requeue, fail-closed termination, successor advancement, PDC movement/selective-assurance planning, reuse of the active ORCH-3/4/5 authorized requeue guard, and immutable observability-only receipts.

## 4. Reuse / non-duplication bindings

The packet deliberately does not create competing PDC/DSAI machinery.

- Main movement classification remains owned by `src/ovc/development/head_churn.py::classify_main_head_movement`.
- Lawful automatic stale-main reconciliation remains bounded by `src/ovc/development/skills/orch345_active.py::build_authorized_requeue_reconciliation` and its active ORCH-3/4/5 authority record.
- Merge authority remains independently owned by existing packet/gate authority and DSAI merge mechanics; SIQ lease ownership is not merge authority.
- The physical serialized lease continues to reuse the existing `ovc-main-integration-lane-v1`; no second integration-lane identity is created.
- Existing PDC stable-main guards remain intact and tested.

## 5. Mechanical tests and QA

Mechanically evaluated exact head: `ab1916cbf57a12ab0837073698279d69e4d2836a`.

### GitHub exact-head assurance

- `tests` workflow run `31754759371`: **PASS**.
  - `OVC final integration window admitted`: PASS.
  - complete repository suite: PASS.
  - Research Console vNext exact maintained API surface: PASS.
  - `runner-parity`: PASS.
  - `pytest-unittest-parity`: PASS.
- `OVC tiered test selection shadow` run `31754759377`: **PASS**.
  - `OVC profile assurance`: PASS, `FINAL_HEAD` profile.
  - `OVC merge readiness`: PASS.
  - compatibility/tiered shadow: PASS.
- Submitted PR reviews: none.
- Blocking review threads: none.
- QA recommendation: **PASS**.

### SIQ invariant coverage

The deterministic tests prove at minimum:

1. multiple READY packets may retain concurrent BASE_INDEPENDENT work;
2. BASE_INDEPENDENT checks cannot acquire the final-integration lease;
3. no more than one packet can own the SIQ lease;
4. FIFO queue-head selection is deterministic;
5. an operator-wait packet does not block an unrelated READY packet;
6. BLOCKED / QUARANTINED packets cannot become queue head;
7. an irrelevant main movement preserves unaffected evidence and reruns mandatory exact final assurance;
8. an integration-relevant main movement reruns impacted/dependent evidence plus mandatory exact final assurance while preserving unaffected evidence;
9. semantic/authority-relevant movement requires full semantic/authority repreflight and automatic requeue fails closed;
10. lawful requeue delegates to the existing active ORCH-3/4/5 requeue guard;
11. lease timeout releases/requeues unless an admitted BASE_SENSITIVE check is actively executing;
12. failed base-sensitive work releases the lease into a fail-closed state;
13. successful integration releases the lease and automatically advances the next READY packet;
14. `parallel_merge`, force-push and history-rewrite paths remain false/unavailable;
15. diagnostic SIQ receipts round-trip immutably and explicitly carry no merge, scientific or governance authority;
16. current PDC `OVC_BASE_MOVED_BEFORE_READINESS`, `OVC_BASE_MOVED_DURING_READINESS` and lease-invalidation guards remain present.

One bounded implementation defect was found during assurance: the new SIQ state schema initially omitted the repository-wide closed-schema declaration. It was corrected by adding `additionalProperties: false`; the complete exact-head assurance was then rerun and passed on `ab1916cb...`.

## 6. Current queue / workflow behavior and why activation is a real authority delta

Current `main` contains the SIQ constitution but the active GitHub workflows still use the pre-SIQ PDC timing:

- `.github/workflows/tests.yml` waits for successful acquisition of the shared final-integration lease **before** starting the expensive required repository/parity assurance;
- `.github/workflows/ovc-tiered-tests.yml` similarly waits for the same acquisition before profile assurance;
- `OVC merge readiness` holds that window through final required-check assurance and stable-main readiness.

That behavior is intentionally left unchanged by the inactive implementation packet. Therefore the repository does **not** yet satisfy the terminal condition that exclusivity begins only for the minimal BASE_SENSITIVE critical section.

A repository search found no exact current authority record activating `OVC.SIQ.RUNTIME.v0.1` or `SIQ-RUNTIME-G1`. The active DSAI2-G3 authority grants bounded ORCH-3/4/5 coordination with PDC serialized integration, but it does not explicitly replace the active final-integration timing contract with SIQ. The SIQ constitutional decision itself explicitly states `runtime_activation_effect=NONE`.

Accordingly SIQ runtime activation is classified as a reserved **capability activation**, not an auto-ratifiable implementation detail.

## 7. Proposed SIQ-RUNTIME-G1 authority delta

A `PASS` authorises only the following bounded development-orchestration change:

`ACTIVATE_SIQ_MINIMAL_CRITICAL_SECTION_AS_FINAL_INTEGRATION_RUNTIME`

with the frozen terminal invariants:

- `PARALLEL_DEVELOPMENT=true`
- `PARALLEL_MERGE=false`
- `BASE_INDEPENDENT_CONCURRENT=true`
- `FINAL_INTEGRATION_LEASE_COUNT=1`
- `SELECTIVE_ASSURANCE_REUSE=true`
- `AUTOMATIC_LAWFUL_REQUEUE=true`
- `IMMEDIATE_SUCCESSOR_ADVANCEMENT=true`
- `RESERVED_AUTHORITY_UNCHANGED=true`

The PASS does **not** grant new packet classes, merge authority, direct-main mutation, force-push/history rewrite, operator-gate bypass, selector/model/family/candidate/theory/semantic promotion, Validation, publication, probability, risk, exposure, trading, execution or agent-write authority.

## 8. Exact work after PASS

1. Re-resolve current main, PR #769 head, reviews and existing PDC/ORCH authority.
2. Reconcile the inactive runtime packet to current main if necessary without force-push/history rewrite.
3. Change the two active workflow admission paths so BASE_INDEPENDENT work completes outside the global lease and only the BASE_SENSITIVE current-main/PDC/exact-final critical section owns the existing serialized lease.
4. Bind the runtime as active while reusing `ovc-main-integration-lane-v1`, PDC movement classification and active ORCH requeue mechanics.
5. Persist SIQ diagnostic receipts without granting authority.
6. Run targeted SIQ/PDC tests, full repository suite, parity assurances, FINAL_HEAD/profile assurance and stable-main merge readiness.
7. Correct bounded defects only; if all pass, squash-integrate the activation packet.
8. Verify from resulting `main` that branch construction remains concurrent, READY ordering is deterministic, lease count is one, lease acquisition starts only at BASE_SENSITIVE work, release occurs immediately after merge/failure/requeue, and the next READY packet advances without an operator pause.
9. Record terminal state `SIQ_ACTIVE_SERIALIZED_MINIMAL_CRITICAL_SECTION` only after the active-path proof passes.

## 9. Rollback

Activation rollback is forward-only: disable the SIQ active binding and restore the prior PDC workflow timing while preserving the same global integration-lane identity, PDC classifier, ORCH authority, all receipts, prior merges, tests and Git history. No force-push, destructive deletion or history rewrite is permitted.

## 10. Warnings / unresolved issues / incidents

- **Blocking authority issue:** exact SIQ runtime activation authority is absent; operator decision required.
- Current early-acquisition PDC workflow behavior is a known pre-activation state, not an implementation defect.
- Unresolved runtime correctness warnings: none after the schema correction and clean rerun.
- Blocking review threads: none.
- Unresolved SIQ/PDC S3/S4 incidents attributable to this packet: none observed.
- Parallel merge remains disabled.

## 11. Decision

Allowed decisions: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`.

**Recommendation: PASS `SIQ-RUNTIME-G1`** for the exact bounded activation delta above.

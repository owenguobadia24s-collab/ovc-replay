# OVC Serialized Integration Queue Runtime Finalisation Plan v0.1

**Plan ID:** `OVC-SIQ-FINALISATION-PLAN-0.1`  
**Programme ID:** `OVC-SERIALIZED-INTEGRATION-QUEUE-RUNTIME-v0.1`  
**Constitution:** `OVC-SERIALIZED-INTEGRATION-QUEUE-v0.1`  
**Constitutional merge:** `a11d6acdb671eaef9e3cf58369d4aae0269f09bb`  
**Execution baseline:** `main@a11d6acdb671eaef9e3cf58369d4aae0269f09bb`  
**Admission basis:** operator command `OVC RUN SIQ FINALISATION` issued 14 August 2026.  
**Target terminal state:** `SIQ_ACTIVE_SERIALIZED_MINIMAL_CRITICAL_SECTION`.

## Purpose
Materialise the executable SIQ runtime while reusing the current PDC main-head classifier, existing serialized final-integration lane identity, DSAI merge/authority mechanics, and active bounded ORCH-3/4/5 runtime. The implementation must not create a second merge authority, lease authority, main-head classifier, orchestration authority, or scientific/governance authority store.

## Frozen invariants
- deterministic FIFO READY queue using materialised `ready_sequence`, then `packet_id`, then candidate head SHA;
- exactly one final-integration lease holder;
- `BASE_INDEPENDENT` work remains concurrent and may never hold the lease;
- only `BASE_SENSITIVE` exact-main work may hold the lease;
- PDC movement classification remains the source of truth for `IRRELEVANT`, `INTEGRATION_RELEVANT`, `SEMANTIC_AUTHORITY_RELEVANT`, and `UNRESOLVED_REQUIRES_FOOTPRINT`;
- unaffected assurance may be reused only where PDC permits it;
- lawful low-risk stale-main requeue reuses the active ORCH-3/4/5 requeue guard and preserves scope/write-set/semantic-owner identity;
- timeout releases/requeues unless an admitted base-sensitive check is actively executing;
- operator-wait/BLOCKED/QUARANTINED candidates never monopolise the queue;
- successor advancement after terminal integration is automatic when the successor independently remains lawful;
- `parallel_merge=false`; permanent integration is squash only; force-push and history rewrite remain prohibited;
- READY, queue position, lease ownership, receipts, assurance PASS and orchestration selection carry no merge/scientific/governance authority.

## Existing machinery reused
- `src/ovc/development/head_churn.py` — PDC main-head movement classification and evidence-reuse doctrine.
- `src/ovc/development/skills/orch345_active.py` — active bounded ORCH-3/4/5 authority and automatic stale-main requeue guard.
- `src/ovc/development/skills/merge_capability.py` — merge preparation/revalidation authority separation.
- existing `ovc-main-integration-lane-v1` — physical serialization identity until a separately governed successor exists.

## Packet
`SIQ-RUNTIME-WP1` implements contracts, schemas, runtime state/projections, deterministic receipts, fixtures and tests. Implementation authority delta is `NONE_INACTIVE_RUNTIME_IMPLEMENTATION`.

## Activation gate
`SIQ-RUNTIME-G1` is `OPERATOR_REQUIRED` unless an exact repository authority record already explicitly grants activation of `OVC-SERIALIZED-INTEGRATION-QUEUE-v0.1` as the controlling final-integration runtime. General ORCH-3/4/5 or PDC authority is not silently treated as SIQ activation authority.

Before G1, runtime code and bindings remain `IMPLEMENTED_INACTIVE`; current workflows retain the existing PDC early-acquisition behaviour. A G1 PASS would authorise only the bounded binding change needed for SIQ minimal-critical-section timing while preserving the existing global lease identity and all reserved boundaries.

## Activation work after lawful G1 PASS
1. Re-resolve current main and candidate head.
2. Bind `.github/workflows/tests.yml` and `.github/workflows/ovc-tiered-tests.yml` so base-independent work completes before global lease acquisition.
3. Acquire the existing serialized final-integration lease only for base-sensitive reconciliation, PDC movement classification, affected closure, exact final assurance and immediate pre-merge pin.
4. Persist SIQ receipts through the runtime without treating them as authority.
5. Flip runtime binding from `IMPLEMENTED_INACTIVE_GATE_READY` to `ACTIVE`.
6. Run targeted tests, complete repository/parity/profile/readiness assurance, squash-integrate, then verify one active path proves concurrent branch work, deterministic READY ordering, lease count one, late acquisition, immediate release and successor advancement.

## Rollback
Before activation, close or supersede the runtime packet. After activation, forward-disable the SIQ active binding and restore prior PDC workflow timing while preserving the global lease identity, PDC classifier, ORCH authority, receipts and Git history. Never force-push or rewrite history.

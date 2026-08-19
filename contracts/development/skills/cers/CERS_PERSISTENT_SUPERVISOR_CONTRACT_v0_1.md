# CERS Persistent Supervisor Contract v0.1

**Programme:** `OVC-DSAI3V-CERS-CONFORMANCE-v0.1`  
**Plan:** `OVC-DSAI3V-CERS-PERSISTENT-SUPERVISOR-ACTIVATION-PLAN-0.1-RATIFIED`  
**Packet:** `CERS-PS-WP1`  
**Status:** INACTIVE / PREACTIVATION  
**Authority effect:** NONE

## Constitutional rules

1. Repository state and accepted owner authority are the only dispatch authority inputs. CERS never manufactures programme, packet, writer, merge, scientific or execution authority.
2. A programme is persistently dispatchable only when an exact active `PersistentProgrammeAdmission` exists. Missing, stale, conflicting or revoked admission is `DENY`.
3. Every dispatch decision binds exact programme, packet, authority source, executor, action, side-effect class, write domain, semantic owner, dependency frontier, currentness frontier and supervisor fencing generation.
4. `OPERATOR_REQUIRED`, reserved authority, `HOLD`, `DISABLE_NEW_DISPATCH`, unknown owner authority, unknown executor, unknown action, unknown side-effect class, unknown write domain and irreversible/unknown side effects are non-dispatchable.
5. The only predeclared repository-writing executor is the existing trusted Packet Executor identity already governed by DSAI. CERS cannot broaden its capability envelope.
6. CERS has no merge capability. Physical integration remains `DSAI_VIT_PHYSICAL_CONTROLLER -> DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY`; parallel physical merge remains false.
7. Direct main mutation, force-push, history rewrite and irreversible external side effects are prohibited.
8. Future programmes are not auto-admitted merely because they exist, are active, or appear in an implementation registry.
9. Quiescence modes are `RUN`, `DRAIN`, `HOLD`, `DISABLE_NEW_DISPATCH`. Before `CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION=PASS`, durable mode must remain `DISABLE_NEW_DISPATCH` for persistent general dispatch.
10. All state transitions are content-addressed, restartable without chat, append-only where decision-bearing, and fail closed on missing evidence.

## Canonical records

### PersistentProgrammeAdmission
Binds exact programme/current-root, governing plan/version, owner authority source, eligible packet/gate classes, allowed side-effect classes, executor binding, write-domain/semantic-owner rule, operator-boundary policy, explicit prohibitions, admission authority source and revocation/quiescence behavior.

### PersistentSupervisorPolicy
Binds allowed authority classes, mandatory deny/park conditions, concurrency/speculation ceilings, physical integration path, future-programme admission policy and rollback mode.

### PersistentExecutorBinding
Binds exact executor identity, existing authority source, action classes, repository/ref write capability, write-domain rule, merge/force-push/history-rewrite capabilities, start-ack/heartbeat/fencing support and side-effect envelope.

### PersistentDispatchAuthorityView
A deterministic derived view over one exact programme/packet/action frontier. It returns `ALLOW`, `PARK`, or `DENY` plus closed reason codes. It is authority-inert.

### PersistentQuiescenceState
Durable mode plus source, generation and effective timestamp/observation identity. Pre-activation persistent-general state is `DISABLE_NEW_DISPATCH`.

## Required deny/park precedence

`HARD_DENY/UNKNOWN` > `QUIESCENCE` > `OPERATOR_BOUNDARY` > `OWNER_AUTHORITY` > `ADMISSION` > `EXECUTOR` > `ACTION_SIDE_EFFECT_WRITE_DOMAIN` > `PREREQUISITE_DEPENDENCY` > `RUNNABLE`.

A lower-priority positive condition cannot override a higher-priority deny/park condition.

## Rollback

Set durable `DISABLE_NEW_DISPATCH`, prevent new starts, reconcile open/unknown ownership, drain/cancel only CERS-owned reversible work, return new work to foreground/ORCH1-assisted invocation, and preserve all leases, dispatches, outcomes, checkpoints, receipts and Git history.

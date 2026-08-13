# OVC DSAI — Operational Throughput Expansion 2026-08-13

**Programme ID:** `OVC-DSAI-THROUGHPUT-20260813`  
**Plan ID:** `OVC-DSAI-THROUGHPUT-EXPANSION-PLAN-0.1`  
**Plan version:** `0.1`  
**Admission basis:** operator instruction: “expand concurrency, train depth, automatic requeue/reconciliation and portfolio dispatch for now and end of day we'll assess if the evidence enables broadening governance authority.”  
**Baseline main:** `bdcf2d96b646b6f5c1e958029bfaf4c782c22d9c`  
**Parent authority:** DSAI2-G3 bounded ORCH-3/4/5 authority already effective on `main`.

## 1. Scope

This is an operational-capacity expansion only. It does not broaden governance authority.

The bounded changes are:

1. increase active ORCH-4/5 parallel construction capacity to **4 build slots**;
2. set an explicit active ORCH-3 packet-train depth cap of **8 packets**;
3. enable deterministic automatic stale-main requeue/reconciliation for approved fail-closed main-head movement classes, capped at **2 automatic attempts per packet**;
4. widen ORCH-5 portfolio dispatch to fill up to four pairwise-compatible build slots while preserving blocked, operator-wait and serial-fallback queues;
5. collect repository evidence through the 2026-08-13 operating day for a later operator assessment of whether governance authority should be broadened.

## 2. Binding non-effects

Authority delta is `NONE`.

The existing DSAI2-G3 limits remain binding:

- packet class remains exactly `LOW_RISK_IMPLEMENTATION`;
- operator-required gates stop;
- `authority_delta != NONE` stops;
- ambiguous/conflicting work falls back to `SERIAL_REQUIRED`;
- parallel merge remains false;
- PDC serialized final-integration window remains mandatory;
- target branch remains `main`, squash merge only;
- direct-main mutation, force-push and history rewrite remain prohibited;
- Validation remains denied;
- scientific/selector/model/family/candidate/theory/semantic/publication/probability/risk/exposure/trading/execution authority remains none.

No end-of-day evidence may self-grant broader governance authority. Any such broadening requires a new explicit operator decision.

## 3. Automatic requeue/reconciliation

Automatic reconciliation is permitted only when all of the following are true:

- DSAI2-G3 authority resolves `ACTIVE_AUTHORIZED` from an authority record present on `main`;
- packet class is `LOW_RISK_IMPLEMENTATION`;
- gate is not operator-required;
- authority delta is `NONE`;
- failure reason is one of:
  - `OVC_BASE_MOVED_BEFORE_READINESS`;
  - `OVC_BASE_MOVED_DURING_READINESS`;
  - `MAIN_ADVANCED_AFTER_ASSURANCE`;
- the packet's write-set, semantic-owner, authority-surface and frozen-surface identities are unchanged;
- current `main` differs from the packet's previous base;
- automatic attempt count is no greater than 2.

A permitted reconciliation requires a fresh branch/reconstruction from current main, preservation of packet scope/identities, fresh exact-head assurance and the existing serialized integration frontier. It never force-pushes or rewrites history.

Any other condition returns `STOP_SERIAL_REQUIRED`.

## 4. Capacity limits

- `max_parallel_builds = 4`
- `max_train_packets = 8`
- `max_auto_requeue_attempts = 2`

These are operational limits, not new authority classes.

## 5. Evidence window

Start: `2026-08-13T08:12:00+01:00`.

At end of day, assess at least:

- real ORCH-3/4/5 packets observed;
- maximum and average simultaneous eligible build slots actually used;
- packet-train depths observed;
- stale-main automatic requeue attempts, successes and exhausted retries;
- serial-fallback classifications and reason codes;
- operator-wait packets respected;
- cross-programme dependency wake-ups;
- discarded assurance cycles;
- false parallel allows;
- parallel merges;
- unresolved S3/S4 incidents attributable to orchestration;
- any authority-boundary violation;
- queue/polling latency where reproducible from repository/GitHub evidence.

The end-of-day assessment may recommend `KEEP_CURRENT`, `TUNE_CAPACITY`, or `PROPOSE_GOVERNANCE_BROADENING`. Only the operator may approve the last option.

## 6. Packet and gate

`DSAI-TE-WP1` implements the bounded capacity profile, active runtime controls, regressions, programme state and evidence-window record.

`DSAI-TE-G1` is `AUTO_RATIFIABLE` only if exact-head repository tests/QA pass, there are no blocking warnings or unresolved review issues, and authority delta remains `NONE`.

Rollback: forward-disable this throughput profile and restore the prior active defaults while preserving DSAI2-G3 authority, PDC serialized integration and all evidence.

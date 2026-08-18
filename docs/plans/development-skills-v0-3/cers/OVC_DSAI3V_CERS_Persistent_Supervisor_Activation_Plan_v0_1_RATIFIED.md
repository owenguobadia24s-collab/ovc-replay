# OVC DSAI3V CERS Persistent Supervisor Activation Plan v0.1 — RATIFIED

**Plan ID:** `OVC-DSAI3V-CERS-PERSISTENT-SUPERVISOR-ACTIVATION-PLAN-0.1-RATIFIED`  
**Programme lineage:** `OVC-DSAI3V-CERS-CONFORMANCE-v0.1`  
**Governing design:** `OVC-DSAI3V-CERS-DESIGN-SPEC-0.1-R1-RATIFIED`  
**Proposed activation gate:** `CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION`  
**Approved proposal baseline:** `main@57995c54e2963984776832b7522841e6b7c834b0` / tree `f67c49b8c3422948bfd96e1e2f7de3f1e19459a8`  
**Operator ratified:** 18 August 2026, `OVC APPROVE CERS-PS-PLAN-RATIFICATION PASS`  
**Status:** RATIFIED — CERS-PS-WP0–WP5 INACTIVE/SHADOW IMPLEMENTATION AUTHORISED; PERSISTENT RUN RESERVED  
**Authority effect:** BOUNDED IMPLEMENTATION AUTHORITY ONLY. CERS-PS-WP0–WP5 may execute under inactive/shadow authority. Persistent `RUN`, programme admission activation, new writer/merge authority, and scientific/Validation/publication/probability/risk/exposure/trading/execution authority remain denied pending `CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION`.

## 0. Purpose

Advance the already-qualified CERS live-pilot capability into the normal persistent DSAI3V supervisor for already-authorised development work, without chat dependency and without creating new programme authority.

The target operational rule is:

> CERS may continuously reconstruct and start already-authorised auto-executable work for explicitly admitted programme roots using the existing trusted execution substrate, while operator-reserved boundaries, programme authority, VIT/SIQ physical integration and durable quiescence remain controlling.

The activation is additive only. CERS remains a liveness supervisor, not an authority source, merge controller, scientific selector, publication mechanism or execution/risk engine.

## 1. Current court-record baseline and gap

CERS-G6 has qualifying post-merge physical-completion evidence for the bounded WP6 pilot, while the Git current pointer remains the historical conditional pre-receipt representation. The bounded live authority remains `CERS_WP6_BOUNDED_UNATTENDED_DISPATCH_ONLY`, and post-pilot quiescence is `DISABLE_NEW_DISPATCH`.

The present runtime is not sufficient for general activation:

- `src/ovc/development/skills/cers/live.py` is hard-bound to programme `OVC-DSAI3V-CERS-CONFORMANCE-v0.1`, packet `CERS-WP6`, semantic owner `CERS`, one pilot branch and exact WP6 paths;
- the reference reconciler rejects non-fixture writing executors and uses pre-activation authority-delta rules;
- the CERS programme-root registry contains only a bounded infrastructure census and is not a general persistent programme-admission register;
- the active action/side-effect registry is explicitly `ACTIVE_BOUNDED_WP6_LIVE_PILOT_ONLY`;
- no persistent event+sweep service lifecycle is currently activated;
- `DISABLE_NEW_DISPATCH` remains the post-pilot state.

Therefore persistent-supervisor activation cannot be achieved by changing one flag. A bounded implementation extension and a new operator activation decision are required.

## 2. Ratified authority envelope before activation

The following implementation work is AUTO-EXECUTABLE before the activation gate:

- contracts, schemas, registries and fixtures for persistent CERS operation;
- deterministic generalisation of reconciliation and dispatch binding;
- read-only programme-root/admission adapters;
- durable supervisor lease, fencing, checkpoint and quiescence state;
- a persistent supervisor service in inactive/shadow mode using an existing authorised local runtime;
- exact binding to the already-qualified existing Packet Executor identity;
- tests, adversarial qualification, DEVOBS, rollback rehearsal and activation-gate preparation;
- PR preparation, VIT/SIQ assurance and eligible automatic squash integration of non-activating packets.

Pre-activation remains DENIED for:

- changing quiescence from `DISABLE_NEW_DISPATCH` to `RUN` for general unattended work;
- unattended invocation outside an explicit persistent-programme admission registry;
- new writer identity or broader Packet Executor write authority;
- direct-main mutation, CERS merge authority, parallel physical merge, force-push/history rewrite;
- automatic admission of future programmes merely because they exist in the repository;
- operator-required packets/gates or any reserved authority;
- ACTIVE_DISCOVERY / ACTIVE_DEVELOPMENT / ACTIVE_VALIDATION grants;
- selector/model/family/candidate/theory/semantic promotion;
- canonical/R2 publication;
- probability/risk/exposure/trading/market-execution authority;
- validation consumption;
- irreversible or unknown external side effects.

## 3. Admission model

Persistent CERS SHALL use a dedicated machine-readable `CERS_PERSISTENT_PROGRAMME_ADMISSION_REGISTRY`.

Each admitted programme entry MUST bind:

- exact `programme_id` and current-state/current-pointer root;
- governing plan and version;
- current authority source;
- eligible packet/gate classes;
- allowed side-effect classes;
- exact executor capability binding;
- programme-specific write-domain/semantic-owner rule;
- operator-boundary policy;
- validation/publication/scientific prohibitions where applicable;
- admission authority source and revocation/quiescence behavior.

Unknown or absent programme admission => DENY.

No future programme becomes persistently dispatchable merely by being created, becoming ACTIVE, or appearing in the implementation registry. New admission requires either explicit authority in that programme's ratified plan or a separate operator decision.

## 4. Ratified packets and gates

### CERS-PS-WP0 — terminal baseline and authority reconciliation

Materialise a new persistent-supervisor baseline that references the already-effective WP6 physical-completion bundle without creating a second CERS-WP6 closeout PR or repeating physical integration.

Required evidence:
- exact WP6 merge/tree/transaction/receipt/proof identities;
- current default DSAI3V/VIT/SIQ substrate;
- current CERS pilot authority and `DISABLE_NEW_DISPATCH` state;
- current executor authority sources;
- current programme-root census;
- explicit statement that general activation remains denied.

**Gate `CERS-PS-G0`: AUTO_RATIFIABLE**, authority delta NONE.

### CERS-PS-WP1 — persistent contracts, schemas and admission registry

Implement:
- `PersistentProgrammeAdmission`;
- `PersistentSupervisorPolicy`;
- `PersistentExecutorBinding`;
- `PersistentDispatchAuthorityView`;
- `PersistentQuiescenceState`;
- exact admission/action/side-effect/reason-code registries.

Conservative rules:
- missing admission => deny;
- owner authority not current => deny;
- operator-required/reserved boundary => park;
- unknown action/side effect/executor/write domain => deny;
- future programme auto-admission => prohibited.

**Gate `CERS-PS-G1`: AUTO_RATIFIABLE**.

### CERS-PS-WP2 — registry-driven live reconciler and coordinator

Generalise the WP6-only live path so runtime behavior is derived from exact registered programme/packet/executor/authority records rather than CERS-WP6 constants.

Required invariants:
- no authority inference;
- exact content-addressed dispatch identity;
- executor identity remains the already-qualified trusted Packet Executor unless separately approved;
- packet execution remains bounded by existing DSAI write authority and packet-declared write domains;
- CERS cannot merge, force-push, rewrite history or write main;
- same durable snapshot => same runnable set and dispatch decision;
- existing programme repair owner receives correctable/blocking failures.

**Gate `CERS-PS-G2`: AUTO_RATIFIABLE**.

### CERS-PS-WP3 — persistent zero-chat supervisor service

Implement an inactive/shadow persistent service using an existing authorised runtime identity/environment. It SHALL:

- acquire one exclusive fenced supervisor lease;
- perform event-triggered reconciliation plus mandatory periodic reference sweeps;
- persist checkpoint/dispatch/worker ownership outside chat state;
- use bounded provider backoff;
- observe exact `START_ACKNOWLEDGED` and heartbeat;
- reconcile ambiguous starts before redispatch;
- respect RUN/DRAIN/HOLD/DISABLE_NEW_DISPATCH immediately;
- expose zero-chat restart proof;
- have no physical-main write or merge capability.

Operational cadence, liveness threshold and reclaim timing SHALL be measured and frozen from observed qualification evidence before activation; they may not be invented ad hoc.

**Gate `CERS-PS-G3`: AUTO_RATIFIABLE**, inactive/shadow only.

### CERS-PS-WP4 — initial persistent programme admission set

Build the first explicit admission registry from machine-readable current programme state and governing authority.

Admission SHALL be conservative. A programme is eligible only where its current plan/state provides sufficient exact information to determine packet authority, prerequisites, operator boundaries, write domains and next packet without chat.

Programmes lacking those surfaces remain excluded with reason codes; their exclusion is not a blocker to activating CERS for the verified subset.

No admission may broaden the underlying programme's authority.

**Gate `CERS-PS-G4`: AUTO_RATIFIABLE** for the inactive admission register only.

### CERS-PS-WP5 — adversarial persistent qualification and capacity freeze

Prove at minimum:
- multiple admitted programmes reconcile deterministically;
- unrelated lanes cannot create false predecessor/lease blocking;
- operator-required gates park while unrelated authorised work proceeds;
- main churn causes selective currentness/placement renewal, not duplicate starts;
- stale fencing generation is rejected;
- unknown-start recovery is idempotent;
- worker loss/reclaim cannot create duplicate authoritative ownership;
- programme authority removal or HOLD immediately prevents new dispatch;
- unregistered programme remains non-dispatchable;
- validation/scientific/publication/risk/execution boundaries remain unreachable;
- existing VIT/SIQ serialized physical integration remains the sole main path;
- zero-chat restart chooses the same lawful next work;
- persistent service outage/restart preserves durable state;
- `DISABLE_NEW_DISPATCH` rollback is executable;
- liveness/cadence/reclaim/backoff and initial worker/build-ahead capacity are frozen from observed evidence.

Initial requested capacity SHALL NOT exceed the already-proven pilot envelope unless separately justified and approved. Default proposal: one worker, speculative depth one, existing visible-train cap, with exact values frozen in G5 evidence.

**Gate `CERS-PS-G5`: AUTO_RATIFIABLE** only if qualification PASS and no blocking warning remains.

### CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION — normal persistent supervision

**OPERATOR_REQUIRED.**

The gate packet MUST state the exact:
- persistent supervisor runtime identity/environment;
- Packet Executor identity and existing authority sources;
- admitted programme set and admission-record hashes;
- eligible packet/gate classes;
- action classes and side-effect classes;
- repository/ref/write-domain rules;
- worker concurrency, speculative depth, visible-train cap;
- event/sweep cadence, liveness threshold, heartbeat and reclaim timing;
- fencing/start-ack/unknown-start semantics;
- VIT/SIQ physical integration path;
- merge and force-push capabilities;
- all G0-G5 tests/QA/adversarial evidence;
- warnings/incidents/exclusions;
- rollback/quiescence procedure;
- current main and exact activation delta.

A PASS may only change persistent CERS from quiescent/inactive to `RUN` for the exact admitted scope. It may not create programme authority or automatically admit future programmes.

## 5. Reserved activation delta

If and only if `CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION=PASS`, CERS may:

1. remain resident/restartable without conversational context;
2. continuously reconcile exact durable repository/provider state;
3. select only exact already-authorised work from the explicit admission registry;
4. invoke the existing trusted Packet Executor unattended for its already-approved bounded packet-branch capability;
5. continue to build ahead only inside existing predecessor/speculation rules;
6. allow existing DSAI/VIT/SIQ machinery to perform separately-authorised QA and physical integration.

The authority delta is **unattended invocation and persistent liveness only**. All programme, scientific, validation, publication, merge, probability, risk, exposure and market-execution authority remains exactly where it already resides.

## 6. Rollback

Durable `DISABLE_NEW_DISPATCH` is the first rollback action.

Then:
- prevent new starts immediately;
- reconcile all owned workers/unknown starts;
- drain or cancel only CERS-owned reversible work according to packet contracts;
- return new work to explicit foreground/ORCH1-assisted invocation;
- preserve leases, dispatch identities, outcomes, checkpoints, DEVOBS, ReceiptStore evidence and Git history;
- do not force-push or delete evidence.

## 7. Terminal state after later activation

After successful activation and post-activation effectiveness evidence:

`CERS_ACTIVE_PERSISTENT_SUPERVISOR_BOUNDED_TO_EXPLICIT_PROGRAMME_ADMISSION_AND_EXISTING_OWNER_AUTHORITY`

Operator ratification authorises only CERS-PS-WP0 through CERS-PS-WP5. General persistent CERS dispatch remains disabled under `DISABLE_NEW_DISPATCH` until `CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION=PASS`.

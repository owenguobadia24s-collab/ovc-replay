# OVC DSAI v0.2 — ORCH-3/4/5 Conformance and Activation Programme

**Programme ID:** `OVC-DSAI-v0.2`  
**Plan ID:** `OVC-DSAI-ORCH345-IMPLEMENTATION-PLAN-0.2`  
**Plan version:** `0.2`  
**Admission basis:** operator instruction in `DSAI2_G0_OPERATOR_ADMISSION.json`  
**Baseline main at admission:** `788dd4ea04b8df53f51369de84fff348de7c61d9`  
**Parent programme:** `OVC-DSAI-v0.1` terminal state `IMPLEMENTED_ORCH2_BOUNDED_PILOTED`  
**Current effective authority at admission:** bounded ORCH-2, `LOW_RISK_IMPLEMENTATION`, `SERIAL_REQUIRED`.

## 1. Purpose

DSAI v0.2 closes the coordination gap left intentionally outside DSAI v0.1. Repository history shows that OVC already performs parallel development through multiple programme branches, while final integration remains serialized and fail-closed. The operational problem is therefore not whether parallel work exists; it is whether the existing concurrency, packet trains and cross-programme dependencies are represented and governed explicitly.

This programme implements and qualifies:

- **ORCH-3:** deterministic multi-packet trains inside one programme;
- **ORCH-4:** deterministic cross-packet conflict classification and bounded parallel construction with serialized final integration;
- **ORCH-5:** cross-programme portfolio scheduling/dispatch over already-authorized packets.

No ORCH-3/4/5 activation occurs until the operator-required `DSAI2-G3` decision is explicitly approved.

## 2. Empirical basis

The frozen corpus `DSAI2_EMPIRICAL_REPOSITORY_CORPUS_v0_1.json` contains 28 coordination events covering 26 distinct PR numbers and eight programmes at the admission snapshot. It includes:

- 8 explicit current-main synchronization/reconciliation events;
- 5 stale-base supersessions;
- 3 otherwise-green assurance cycles discarded by main-head movement;
- 1 approved-gate stale rematerialization;
- 1 non-mergeable reconciliation reconstruction;
- 1 documented CI head-of-line blocking defect;
- 2 PDC serialized-final-integration corrections;
- 2 cross-programme dependency events;
- 2 multi-packet train observations;
- live simultaneous PYT/C2P packet construction plus a wider concurrent-programme snapshot.

The corpus is development-operations evidence only. It grants no scientific, market, selector, semantic, publication, Validation, probability, risk, exposure, trading or execution authority.

## 3. Constitutional architecture

### ORCH-3 — packet trains

ORCH-3 may form a deterministic sequential train only from packets that:

1. belong to the same programme;
2. are `LOW_RISK_IMPLEMENTATION`;
3. have all prerequisites satisfied;
4. have gate class `AUTO_EXECUTABLE` or `AUTO_RATIFIABLE`;
5. have `authority_delta=NONE`;
6. remain inside existing packet-scoped write and semantic-owner authority.

Every packet still receives its own branch, tests, QA, decision, exact-head revalidation and squash integration. ORCH-3 removes unnecessary stop/restart coordination; it does not turn a programme into one long-lived feature branch.

### ORCH-4 — parallel build, serialized integration

ORCH-4 classifies every candidate pair using:

- normalized exact write sets;
- declared cross-packet dependency edges;
- semantic-owner overlap;
- authority-surface overlap;
- frozen-control overlap;
- gate class and authority delta.

The only parallel-safe classification is `PARALLEL_BUILD_ALLOWED_SERIAL_INTEGRATION`. Any overlap, dependency, ambiguity, reserved gate, non-NONE delta or non-eligible packet class collapses to `SERIAL_REQUIRED`.

ORCH-4 does **not** authorize parallel merge. The already-completed PDC invariant remains binding:

`PARALLEL_BUILD_SERIALIZED_FINAL_INTEGRATION_WINDOW_ACTIVE`.

Every main integration uses the repository-wide serialized final-integration window, exact base/head/check revalidation and squash merge only.

### ORCH-5 — portfolio scheduler

ORCH-5 is a scheduler, not an authority source. It may select among packets whose authority and eligibility already resolve independently. It may:

- wake a packet when cross-programme prerequisites become satisfied;
- select independent ready packets for bounded parallel construction;
- leave operator-gated packets waiting without blocking unrelated work;
- deterministically fall back to serial execution when ORCH-4 reports conflict;
- preserve explicit queue/wait/block reasons.

It may not create programme authority, satisfy a missing prerequisite by inference, cross an operator gate, change packet class, grant write/merge rights, or consume Validation/scientific authority.

## 4. Work packets and gates

### DSAI2-WP0 — empirical admission and programme freeze

Materialize the operator admission, empirical repository corpus, plan, shadow policy and machine-readable state.

**Gate:** `DSAI2-G0` is satisfied by the explicit operator instruction admitting creation and implementation of this programme. Its effect is conformance implementation and gate preparation only.

### DSAI2-WP1 — ORCH-3/4/5 conformance runtime

Implement deterministic, side-effect-free primitives for:

- packet descriptors and write-set identities;
- ORCH-3 packet-train planning;
- ORCH-4 pair classification and conflict matrices;
- ORCH-5 portfolio scheduling;
- empirical-corpus analysis;
- activation-readiness construction;
- fail-closed future authority resolution.

Execution mode remains `SHADOW_ONLY`.

### DSAI2-WP2 — empirical replay qualification

Replay the frozen repository corpus through the conformance runtime and prove:

- ORCH-3 need signal is present from real packet-train history;
- ORCH-4 need signal is present from live parallel construction plus observed head churn;
- ORCH-5 need signal is present from cross-programme dependency and concurrent-programme history;
- ambiguous or overlapping packets deterministically fall back to serial;
- PDC serialized final integration remains mandatory;
- no shadow result self-grants authority.

**Gate `DSAI2-G2`: AUTO_RATIFIABLE** if tests and QA PASS and authority delta remains NONE.

### DSAI2-G3 — bounded ORCH-3/4/5 activation

**Gate class: OPERATOR_REQUIRED.**

Proposed exact activation delta:

- ORCH-3: `ACTIVE_BOUNDED_LOW_RISK_PACKET_TRAINS`;
- ORCH-4: `ACTIVE_BOUNDED_PARALLEL_BUILD_SERIAL_INTEGRATION`;
- ORCH-5: `ACTIVE_BOUNDED_PORTFOLIO_DISPATCH_ONLY`;
- enabled packet class: exactly `LOW_RISK_IMPLEMENTATION`;
- automatic gate handling: only wholly auto-executable/auto-ratifiable `authority_delta=NONE`;
- all main integrations: existing PDC serialized final-integration window, squash only;
- direct main mutation: false;
- force push: false;
- history rewrite: false;
- operator-required gates: stop;
- Validation: denied;
- scientific/selector/model/family/candidate/theory/semantic/publication/probability/risk/exposure/trading/execution authority: none.

No activation record becomes effective merely because its schema or resolver exists. The exact approved authority record must be present on `main`.

### DSAI2-WP3 — post-G3 authority materialisation

Only after explicit `DSAI2-G3 PASS`, materialize the immutable bounded authority record, resolve it fail-closed from main and update programme state.

### DSAI2-WP4 — bounded live orchestration pilot

Run a bounded live pilot using already-authorized low-risk development packets:

1. one ORCH-3 same-programme packet train;
2. one ORCH-4 pair admitted for parallel construction but serialized integration;
3. one ORCH-5 portfolio schedule containing at least one cross-programme dependency and one operator-wait packet.

No new packet class or scientific authority may be introduced for the pilot.

### DSAI2-G4 — post-activation assurance

AUTO-ratifiable only if the pilot demonstrates exact authority containment, deterministic conflict handling, zero false parallel allows, serialized integration, reproducible receipts and no unresolved S3/S4 incident.

Target terminal state:

`IMPLEMENTED_ORCH345_BOUNDED_PARALLEL_BUILD_SERIAL_INTEGRATION_PORTFOLIO_DISPATCH`.

## 5. Required records

Every packet must preserve the OVC programme-state fields:

`packet_id`, `plan_id`, `plan_version`, `status`, `prerequisites`, `authority_required`, `authority_delta`, `baseline_commit`, `branch`, `candidate_commit`, `tests`, `qa_packet`, `decision_record`, `merge_commit`, `blockers`, `next_packet`.

ORCH-4/5 additionally require immutable packet descriptors, write-set hashes, conflict matrices, scheduler decisions and any serial-fallback reason.

## 6. Failure and rollback

- Any ambiguous conflict => `SERIAL_REQUIRED`.
- Any stale base/head at integration => re-preflight against current main.
- Any operator gate or non-NONE authority delta => stop.
- Any unresolved S3/S4 incident attributable to ORCH-3/4/5 => block activation/continuation.
- Rollback after activation is forward-disable to bounded ORCH-2 `SERIAL_REQUIRED`, preserving all branches, receipts and historical decisions.
- Never force-push, rewrite history, delete evidence or weaken tests to obtain a pass.

## 7. Explicit non-effects

This plan does not activate a selector, model, family, candidate, theory or semantic grammar; does not consume Validation; does not publish canonical/R2 evidence; does not authorize provider intake, probability, risk, exposure, trading or execution; and does not grant unrestricted agent-write authority.

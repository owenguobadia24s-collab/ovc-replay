# OVC DSAI v0.3 — Continuous Packet Execution and Ordered Landing Train

**Programme ID:** `OVC-DSAI-v0.3`  
**Plan ID:** `OVC-DSAI-CONTINUOUS-EXECUTION-LANDING-TRAIN-IMPLEMENTATION-PLAN-0.1`  
**Plan version:** `0.1`  
**Admission basis:** operator instruction recorded in `DSAI3_G0_OPERATOR_ADMISSION.json`  
**Baseline main at admission:** `7e5db8b99464b7afebdbce703cf3377d9b65ff82`  
**Parent authority:** OVC-DSAI-v0.2 terminal `IMPLEMENTED_ORCH345_BOUNDED_PARALLEL_BUILD_SERIAL_INTEGRATION_PORTFOLIO_DISPATCH`.

## 1. Purpose

DSAI v0.3 closes the execution gap exposed by live ORCH-3/4/5 operation. DSAI v0.2 can select packet trains, classify parallel-safe construction, schedule a portfolio and decide whether stale-main requeue is lawful, but the automatic entrypoint currently terminates at `DECISION_SELECTED`. The repository already has an operator-activated Serialized Integration Queue (`OVC.SIQ.RUNTIME.v0.1`) with FIFO READY ordering, one late BASE_SENSITIVE lease, automatic lawful requeue policy and immediate successor advancement. DSAI v0.3 therefore does **not** create or replace the merge queue. It adds the missing persistent packet actuator and binds ORCH-3/4/5 execution to the existing SIQ runtime.

The target operating model is:

`parallel construction lanes -> persistent ordered landing train -> one serialized squash integration point`.

The programme must reduce avoidable main-head churn without weakening exact-head assurance, serialized integration, operator-reserved boundaries or the existing prohibition on force-push/history rewrite.

## 2. Operator command semantics

When v0.3 activation is eventually approved:

- `OVC RUN <programme-or-packet>` starts at the named scope and continues through every subsequent eligible auto-executable/auto-ratifiable successor until a mandatory stop or explicit boundary.
- `OVC CONTINUE [packet]` resumes from the named packet, or the first incomplete eligible packet if omitted, and continues under the same rule.
- `OVC RUN ONLY <packet>` / `OVC CONTINUE ONLY <packet>` executes exactly that packet plus required integration/closeout, then stops.
- `OVC RUN ... UNTIL <gate-or-packet>` adds an explicit stop boundary.
- Continuation authority is persisted in repository state; chat history is never the sole continuation source.
- A completed packet, PASS QA, auto-ratifiable gate, opened PR, eligible merge, successful squash merge, or successor READY state is not by itself a stop condition.

This section is implementation target semantics only until `DSAI3-G7` operator activation.

## 3. Constitutional integration architecture

### 3.1 Parallel construction lanes

ORCH-3/4/5 retain their active v0.2 bounded authority for already-authorized `LOW_RISK_IMPLEMENTATION` work. DSAI v0.3 does not broaden packet classes, write domains, scientific authority or merge concurrency.

### 3.2 Existing SIQ is the ordered landing train

The active `OVC.SIQ.RUNTIME.v0.1` constitution/runtime remains the sole landing-queue owner. DSAI v0.3 MUST reuse its existing `QueueCandidate`, `QueueState`, FIFO `ready_sequence`, single BASE_SENSITIVE lease, PDC movement classification, selective assurance reuse and immediate-successor rules rather than duplicating or superseding them.

Only the SIQ queue-head candidate may perform base-sensitive final merge assurance against current `main`. Waiting candidates preserve immutable payload/scope identities and queue position but do not repeatedly consume final-main assurance that is guaranteed to become stale behind predecessors.

After the queue-head packet integrates, the next candidate is reconciled from the new lawful main without force-push/history rewrite, then receives fresh exact-head assurance before squash merge.

### 3.3 Build scheduling is separate from merge scheduling

ORCH-5 allocates construction capacity. Landing-train state allocates integration order. A packet may build concurrently without competing for the current main integration lease.

### 3.4 Automatic packet closeout

For a wholly auto-executable packet, the target lifecycle is:

`READY -> RUNNING -> IMPLEMENTED -> QA_REVIEW -> APPROVED -> LANDING_QUEUED -> FINAL_ASSURANCE -> MERGED -> COMPLETED -> SUCCESSOR_RELEASED`.

Post-merge receipts and state projections must not create an avoidable second base-sensitive integration contest. Where a resulting merge SHA cannot be known pre-merge, the post-merge record is a bounded forward projection over the immutable merge event, not a new competitor for the landing train.

## 4. Work packets and gates

### DSAI3-WP0 — admission, baseline and programme materialisation
Materialise this plan, the operator admission, current-main reconciliation, programme state and no-activation invariants.

**Gate `DSAI3-G0`: OPERATOR ADMISSION RECORDED.** The operator instruction authorises bounded conformance implementation and gate preparation only.

### DSAI3-WP1 — normative contracts and state model
Implement contracts/schemas/fixtures for:
- `ContinuationMandate`;
- `ExecutionLifecycleReceipt`;
- `RequeueExecutionIntent`;
- `IntegrationCapabilityProfile`;
- `SIQBindingRecord`;
- explicit command boundary semantics.

`LandingQueueEntry` / `LandingTrainState` are **not** new DSAI3-owned objects; the existing SIQ `QueueCandidate` / `QueueState` remain authoritative for queue mechanics.

**Gate `DSAI3-G1`: AUTO_RATIFIABLE**, authority delta `NONE`.

### DSAI3-WP2 — deterministic ORCH-to-SIQ binding planner
Implement side-effect-free binding from authorized ORCH packet selection into the existing SIQ READY admission/order/queue-head/final-assurance model, plus deterministic restart from repository evidence. No second landing queue may be created.

Required invariants:
- exactly one train-front integration candidate;
- no parallel merge;
- only train-front performs base-sensitive final assurance;
- queue position never grants authority;
- operator-gated/non-NONE-delta candidates do not enter automatic landing;
- deterministic order and reason codes.

**Gate `DSAI3-G2`: AUTO_RATIFIABLE**, authority delta `NONE`, shadow only.

### DSAI3-WP3 — persistent continuation resolver
Implement repository-backed continuation mandates and successor release semantics. Prove that a command starting at one packet can resolve consecutive auto-executable successors until a genuine mandatory stop without consulting chat state.

**Gate `DSAI3-G3`: AUTO_RATIFIABLE**, authority delta `NONE`, shadow only.

### DSAI3-WP4 — packet execution lifecycle sandbox actuator
Implement a sandbox/non-side-effecting actuator that consumes ORCH selection plus continuation state and emits the complete lifecycle:
`DECISION_SELECTED -> EXECUTION_STARTED -> TESTS_COMPLETED -> QA_COMPLETED -> GATE_DECIDED -> LANDING_QUEUED -> FINAL_ASSURANCE -> MERGED/REQUEUED/BLOCKED -> CLOSEOUT_COMPLETED -> SUCCESSOR_RELEASED`.

No production repository write/merge is activated in WP4.

**Gate `DSAI3-G4`: AUTO_RATIFIABLE**, authority delta `NONE`.

### DSAI3-WP5 — automatic stale-main reconciliation and capability-aware integration
Connect the existing lawful stale-main requeue decision to a sandbox execution plan that:
- creates a fresh-branch intent from current main;
- preserves packet/scope/write-set/semantic-owner identities;
- never force-pushes or rewrites history;
- caps automatic attempts at the active policy;
- understands integration capability such as `native_stack_merge=false`;
- avoids constructing disposable native merge stacks when the active merger cannot consume them;
- treats post-merge closeout as a projection rather than a second competing landing packet where lawful.

**Gate `DSAI3-G5`: AUTO_RATIFIABLE**, authority delta `NONE`.

### DSAI3-WP6 — integrated three-lane rehearsal
Run a deterministic synthetic/fixture rehearsal with at least three independent programme lanes and at least two auto-executable packets per lane.

Acceptance:
- parallel-safe build selections occur;
- one ordered landing train is formed;
- only the front candidate runs base-sensitive final assurance;
- artificial main advancement causes automatic lawful reconciliation without operator intervention;
- successor packets release automatically;
- an injected operator-required boundary stops exactly that lane at the boundary while unrelated lanes remain schedulable;
- zero parallel merges, force pushes, history rewrites or authority false-allows;
- lifecycle receipts prove actual simulated start/completion/requeue/landing events rather than decision selection alone.

**Gate `DSAI3-G6`: AUTO_RATIFIABLE**, authority delta `NONE`.

### DSAI3-G7 — activate continuous packet executor and SIQ actuation binding
**OPERATOR_REQUIRED.**

Proposed future activation delta, if explicitly approved:
- persistent continuation mandates for existing authorized low-risk packet classes;
- automatic successor execution until a mandatory stop;
- write-capable stale-main requeue/reconciliation within existing attempt caps;
- write-capable binding to the already-active SIQ ordered landing queue;
- automatic eligible squash integration remains serialized and exact-head revalidated;
- automatic closeout/successor release;
- execution lifecycle receipts.

Explicitly unchanged:
- enabled packet class remains exactly existing authorized low-risk classes;
- parallel merge remains false;
- target branch remains `main`;
- squash-only final integration;
- no direct main mutation;
- no force-push/history rewrite;
- operator-required gates stop;
- no Validation, selector, model, family, candidate, theory, semantic promotion, canonical/R2 publication, probability, risk, exposure, trading or execution authority.

### DSAI3-WP7 — authority materialisation and bounded live pilot
Only after explicit `DSAI3-G7 PASS`, materialise the exact authority record and run a bounded live pilot across multiple low-risk programme lanes.

### DSAI3-G8 — post-activation assurance
AUTO-ratifiable only if the live pilot proves:
- deterministic continuous successor execution;
- ordered one-at-a-time landing;
- no discarded full final-assurance cycles for non-front waiting candidates;
- bounded successful stale-main recovery;
- zero false authority allows;
- zero parallel merges;
- no unresolved S3/S4 incident;
- reproducible lifecycle receipts.

Target terminal state:
`IMPLEMENTED_CONTINUOUS_PACKET_EXECUTION_ORDERED_LANDING_TRAIN`.

## 5. Branch, integration and evidence discipline

- One bounded branch per packet or explicitly grouped packet set.
- Every packet starts from latest lawful main after preflight.
- Waiting landing candidates are not permanent bases for successors.
- Every final merge pins exact head/base/checks/QA/scope/authority.
- No force-push, history rewrite, direct main mutation or evidence deletion.
- Durable programme state is the continuation source of truth.
- Operator-required authority cannot be inferred from code, tests, queue position or prior ORCH authority.
- Large traces/caches stay outside Git; compact deterministic receipts remain in Git.

## 6. Failure and rollback

Any authority ambiguity, frozen-surface drift, packet-class expansion, changed write-set/semantic owner, exhausted requeue cap, unresolved blocking review, non-reproducible artifact or S3/S4 incident stops the affected lane fail-closed.

Before G7, rollback is removal/disablement of v0.3 shadow/sandbox surfaces while preserving v0.2 ORCH-3/4/5 authority and the already-active SIQ runtime unchanged. After G7, rollback is forward-disable of the v0.3 actuator/SIQ-binding runtime back to the v0.2 bounded ORCH-3/4/5 decision/dispatch model plus existing SIQ runtime, preserving all historical receipts and merged packets.

## 7. Acceptance benchmark

The programme is not considered ready for activation until a fixture proves:

> Three independent programmes build concurrently, at least two packets per programme complete, one deterministic serialized landing train governs integration, waiting packets do not run disposable final-main assurance, artificial main advancement is reconciled automatically, every wholly auto-executable packet ratifies/lands/closes/releases its successor without operator intervention, and the first genuine operator-required boundary stops exactly where required.

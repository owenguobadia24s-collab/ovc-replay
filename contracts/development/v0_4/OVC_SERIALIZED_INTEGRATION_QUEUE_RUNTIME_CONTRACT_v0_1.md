# OVC Serialized Integration Queue Runtime Contract v0.1

## Identity
- runtime: `OVC.SIQ.RUNTIME.v0.1`
- constitution: `OVC-SERIALIZED-INTEGRATION-QUEUE-v0.1`
- policy: `OVC.SIQ.v0.1`
- owner lineage: `OVC-PARALLEL-DEVELOPMENT-HEAD-CHURN-v0.1`
- implementation programme: `OVC-SERIALIZED-INTEGRATION-QUEUE-RUNTIME-v0.1`

## Constitutional role
The SIQ runtime is deterministic development-orchestration machinery. It does not own merge authority, scientific authority, programme authority, gate authority, PDC movement semantics, ORCH-3/4/5 authority or the physical global integration-lane identity.

## Runtime state
A queue generation consists of immutable candidate snapshots, deterministic READY ordering, an optional single lease holder, and a generation number. READY admission requires implementation completion, QA PASS, classified authority, absence of blocking review/issue/warning, preliminary/base-independent assurance PASS, rollback, and a pinned candidate/dependency footprint.

Operator-required, BLOCKED and QUARANTINED candidates are represented explicitly and cannot become queue head until their independent blockers are lawfully resolved.

## Assurance partition
`BASE_INDEPENDENT` includes packet-local tests, schema/fixture validation, immutable bound evidence, candidate-correctness assurance and QA evidence generation. It must never hold the final-integration lease.

`BASE_SENSITIVE` includes current-main reconciliation, PDC head-movement classification, affected dependency closure, exact-tree merge readiness, mandatory final-head assurance and the immediate pre-merge base/head pin. Only this class may hold the lease. Unknown assurance classes fail closed.

## Lease
The runtime exposes one logical holder maximum. Physical lease execution reuses the existing PDC global final-integration lane; it does not create a second concurrency group or credential path. Lease target/warning/requeue budgets remain 300/600/900 seconds. A timeout beyond 900 seconds releases and requeues unless an admitted base-sensitive check is actively executing. Lease possession is evidence of serialization only and is never merge authority.

## Main movement and selective reuse
The runtime MUST call the existing PDC `classify_main_head_movement` implementation.
- `IRRELEVANT`: reuse unaffected completed evidence and rerun mandatory exact final assurance.
- `INTEGRATION_RELEVANT`: rerun impacted/dependent assurance plus mandatory exact final assurance; reuse unaffected evidence.
- `SEMANTIC_AUTHORITY_RELEVANT`: no automatic reuse; full semantic/authority repreflight is required and the packet remains blocked until lawfully resolved.
- `UNRESOLVED_REQUIRES_FOOTPRINT`: fail closed pending a sufficient dependency footprint.

Automatic requeue for eligible low-risk packets MUST reuse active ORCH-3/4/5 `build_authorized_requeue_reconciliation`. SIQ may not broaden its reason codes, packet classes, gate classes or attempt cap.

## Successor advancement
After an externally observed successful squash merge, failure, timeout or requeue, the lease releases immediately. The next independently READY candidate becomes queue head deterministically. Operator-wait packets do not block unrelated READY packets.

## Receipts
SIQ diagnostic receipts are immutable, content-addressed observability records. They MUST state that READY status, queue position, lease ownership, assurance success and orchestration selection are non-authoritative. Receipt persistence cannot manufacture execution start/completion or merge authority.

## Prohibitions
- parallel merge;
- force-push;
- history rewrite;
- direct-main mutation by queue runtime;
- authority inference from queue state;
- scientific/semantic/Validation/publication/probability/risk/exposure/execution authority;
- weakening PDC stable-main guards or existing packet/gate authority.

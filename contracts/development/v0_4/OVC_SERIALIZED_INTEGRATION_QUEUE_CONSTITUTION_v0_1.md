# OVC Serialized Integration Queue Constitution v0.1

## Identity

- **constitutional object:** `OVC-SERIALIZED-INTEGRATION-QUEUE-v0.1`
- **parent programme:** `OVC-PARALLEL-DEVELOPMENT-HEAD-CHURN-v0.1`
- **parent contract:** `contracts/development/v0_3/OVC_PARALLEL_DEVELOPMENT_HEAD_CHURN_CONTRACT_v0_1.md`
- **policy registry:** `registries/development/OVC_SERIALIZED_INTEGRATION_QUEUE_POLICY_v0_1.json`
- **operator decision:** PASS — explicit instruction on 13 August 2026 to add the OVC Serialized Integration Queue to the development constitution.
- **authority effect:** development-orchestration constitution only. No market, scientific, semantic, Validation, publication, probability, risk, exposure, execution or agent-write authority.

## Constitutional amendment rule

This contract prospectively supplements and, where more specific, supersedes the **Serialized integration lane** section of the parent v0.1 contract. The parent rules remain intact unless explicitly amended here: concurrent isolated packet construction remains lawful; permanent integration into `main` remains serialized; exact final integration assurance remains mandatory; a readiness PASS remains evidence rather than merge authority; force-push and history rewrite remain forbidden.

The purpose of this amendment is to ensure that serialization applies only to the smallest phase that truly requires exclusive access to the next generation of `main`. Expensive base-independent build, test and QA work MUST NOT hold the repository-wide final-integration lease.

## 1. Queue model

OVC SHALL maintain one logical Serialized Integration Queue for permanent `main` integration.

- Build, packet-local tests, repository tests, QA preparation and non-reserved evidence work MAY execute concurrently on isolated packet branches.
- A candidate enters the READY queue only after all admission conditions in the policy registry are satisfied.
- Queue order is deterministic FIFO by materialized `ready_sequence`; ties are resolved by `packet_id` and then pinned candidate head SHA.
- Queue position grants no authority and does not imply merge eligibility.
- Exactly one candidate may own the final-integration lease at a time.
- `parallel_merge` remains `false`.

## 2. Queue admission

A permanent candidate MAY enter READY only when:

1. bounded implementation is complete;
2. required packet-local QA recommends PASS;
3. the authority delta is classified and any operator-required gate is already satisfied or the candidate is marked STOP rather than queued for merge;
4. no blocking review, issue or unresolved correctness warning remains;
5. required preliminary/base-independent assurance has passed on the candidate head;
6. rollback is defined;
7. the candidate head, packet identity, plan identity and dependency footprint are pinned.

A candidate missing any admission item remains BUILD/QA/BLOCKED and MUST NOT acquire the lease.

## 3. Assurance partition

Assurance is divided into two constitutional classes.

### BASE_INDEPENDENT

Checks whose result remains valid when unrelated `main` movement does not intersect their declared dependency or integration footprint. Examples include packet-local deterministic tests, schema/fixture validation, scientific/replay evidence bound to unchanged immutable inputs, broad candidate correctness checks and QA evidence generation.

BASE_INDEPENDENT assurance SHOULD complete before queue admission and MUST NOT hold the final-integration lease.

### BASE_SENSITIVE

Checks whose truth depends on the exact current `main`, candidate/base composition or exact integration tree. This class includes current-main reconciliation, PDC head-movement classification, affected dependency closure, exact-tree/merge-readiness evaluation, required final-head assurance and the immediate pre-merge stable-main/head-pin check.

Only BASE_SENSITIVE work may hold the final-integration lease.

Owning plans may require additional exact-head tests. This constitution does not waive those tests; it requires them to be classified explicitly rather than treating all assurance as lease-holding by default.

## 4. Final-integration lease

The queue head may acquire the lease only after READY admission.

The default lease budget is:

- target: `< 300 seconds`;
- warning: `> 600 seconds`;
- release-and-requeue threshold: `> 900 seconds` unless a declared admitted BASE_SENSITIVE check is actively executing.

While a lease is held:

1. unrelated permanent merges to `main` are prohibited;
2. unrelated branch development and non-integration CI remain allowed;
3. the candidate re-pins current `main` and classifies movement since its prior baseline;
4. only invalidated/dependent assurance plus mandatory exact final assurance is rerun;
5. the candidate verifies the PR head and `main` are unchanged immediately before merge;
6. an eligible candidate squash-merges immediately after PASS;
7. the lease is released immediately after merge, failure, timeout, operator stop or requeue decision.

A lease is not merge authority. Existing packet/gate authority remains controlling.

## 5. Main movement and automatic requeue

When `main` moves for a queued candidate, OVC SHALL use the existing PDC classification rather than invalidate work by commit count alone.

- `IRRELEVANT`: retain unaffected evidence; re-pin base and run mandatory exact final assurance only.
- `INTEGRATION_RELEVANT`: reconcile to current `main`; rerun impacted/dependent assurance and mandatory exact final assurance; retain unchanged bound evidence.
- `SEMANTIC_AUTHORITY_RELEVANT`: perform full semantic/authority re-preflight and regenerate dependent evidence as required; BLOCK or SUPERSEDE if the packet premise changed.
- `UNRESOLVED_REQUIRES_FOOTPRINT`: fail closed until a sufficient dependency footprint exists.

Automatic requeue MUST preserve packet scope identity, write-set identity and semantic-owner identity. It MUST NOT force-push, rewrite history, weaken tests, silently change a frozen contract or broaden authority.

## 6. Immediate successor advancement

After one candidate integrates, the next READY candidate becomes queue head without an operator pause when:

- its authority remains wholly auto-executable or its required operator authority was already explicitly granted;
- its prerequisites remain satisfied on current `main`;
- PDC movement classification is resolvable;
- no new blocker appears.

The queue MUST NOT stop merely because a prior candidate merged. A new operator stop is required only for a genuine reserved authority change, blocker, ambiguity or stated boundary.

## 7. Observability and receipts

Every queue transition SHOULD be materialized as diagnostic development evidence containing at least:

`queue_id`, `ready_sequence`, `packet_id`, `plan_id`, `candidate_head_sha`, `baseline_main_sha`, `queue_state`, `lease_state`, `lease_acquired_at`, `lease_released_at`, `movement_classification`, `assurance_reused`, `assurance_rerun`, `decision`, `merge_sha` and `reason_codes`.

Queue receipts are observability only. They cannot grant authority, alter scientific identities or manufacture execution completion.

## 8. Failure and rollback

- A failed BASE_SENSITIVE check releases the lease and returns the candidate to the smallest lawful state: REQUEUE, BLOCKED, QUARANTINED or OPERATOR_REQUIRED.
- A GitHub/CI delay that exceeds the lease threshold releases and requeues unless an admitted BASE_SENSITIVE check is actively executing.
- Repeated requeue pressure is an orchestration-health signal, not permission to weaken stable-main checks.
- Rollback is forward-only: supersede or revert SIQ policy/runtime changes while preserving historical queue, readiness and merge evidence.

## 9. Constitutional invariant

**Parallel development is broad; permanent integration is singular; exclusivity begins as late as possible and ends immediately after the exact-head decision.**

No packet may monopolize the integration lane while performing work that does not require the exact next generation of `main`.

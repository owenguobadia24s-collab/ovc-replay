# OVC CI Performance Remediation Protocol

Implementation Plan v0.1

## Document control

- **programme_id:** `OVC-CI-PERFORMANCE-REMEDIATION-v0.1`
- **plan_id:** `OVC-CIPR-IMPLEMENTATION-PLAN-0.1`
- **repository:** `owenguobadia24s-collab/ovc-replay`
- **baseline_main:** `3057d42e8a228a862dc37bddfa0e462d64bfe72f`
- **prepared:** `2026-08-12`
- **operator instruction:** `Construct and execute a remediation protocol`
- **source audit:** complete CI-performance audit immediately preceding this instruction
- **status:** `RATIFIED_FOR_BOUNDED_IMPLEMENTATION`
- **authority effect:** `NONE` outside development CI/orchestration assurance.

## 0. Decision and problem statement

Execute a staged CI-performance remediation that removes avoidable cross-PR head-of-line blocking, makes latency measurable, classifies workflow inventory, and prepares—but does not silently activate—a later heavy-suite parallelisation change.

The audit established two dominant costs: (1) the repository-wide merge-readiness concurrency lane is acquired before canonical tests finish and can therefore hold unrelated PRs behind a polling runner for minutes; and (2) most canonical-suite runtime is concentrated in a small number of heavyweight assurance/evidence tests. GitHub runner/bootstrap overhead is not the primary bottleneck.

This protocol preserves Development Acceleration v0.2 and PDC v0.1 assurance semantics unless an explicit later gate says otherwise. In particular, exact-head canonical assurance, stable-main verification, per-PR cancellation, fail-closed base movement and one logical serial integration evaluation remain mandatory.

## 1. Frozen safety constraints

Until `CIPR-G4-SUITE-TOPOLOGY` is separately approved:

1. `.github/workflows/tests.yml` remains the canonical complete repository-suite workflow and its standalone complete-suite command is not removed, skipped, sharded or weakened by this programme.
2. The authorised PR-listener surface remains exactly `tests.yml` plus `ovc-tiered-tests.yml`.
3. `OVC merge readiness` remains repository-wide serial with `cancel-in-progress: false`.
4. The serial lane may be held only for final integration evaluation; waiting for canonical tests must happen before acquiring that lane.
5. `main` must equal the PR event base when final readiness starts and must remain unchanged through the final evaluation.
6. FAST/PACKET/FINAL_HEAD selection remains advisory early assurance only; it never substitutes for the canonical complete repository suite.
7. No scientific, semantic, selector, family, Validation, publication, probability, risk, exposure, trading, execution or agent-write authority is created.
8. No force-push, history rewrite, destructive cleanup or deletion is authorised.

## 2. Remediation architecture

### Stage A — decouple test waiting from the serial integration lane

Introduce a non-serial `canonical-tests-observed` job in `ovc-tiered-tests.yml`. It waits for the canonical `tests` check on the exact PR head outside the global integration concurrency group. Only after that job passes may `OVC merge readiness` enter `ovc-main-integration-lane-v1`.

Inside the serial lane, readiness performs a bounded final evaluation only: verify current main equals the event base, re-read the exact-head canonical `tests` check, verify success, re-read main, fail closed if main moved, and exit. No polling/sleep loop may remain inside the serial lane.

This is an implementation refinement of PDC v0.1, not a relaxation: final integration evaluation remains globally serialized, but unrelated PRs no longer queue behind another PR merely because its canonical test workflow is still running.

### Stage B — CI latency observability

Emit compact structured `OVC_CI_METRIC` JSON log records from the canonical-test observer and integration-lane evaluator. Minimum metrics:

- `canonical_tests_observation_wait_ms`;
- `integration_lane_evaluation_ms`;
- exact head SHA;
- terminal observation/evaluation result.

No metric grants authority or substitutes for required checks.

### Stage C — workflow inventory classification

Materialise a machine-readable inventory policy distinguishing current PR CI, active manual operations, historical/manual verification and temporary workflows. This stage is classification/documentation first; destructive deletion or retirement remains outside this protocol unless separately authorised.

### Stage D — heavyweight suite topology

The audit identified a small number of heavyweight tests/benchmarks dominating canonical-suite wall time. Re-architecting the canonical complete-suite topology (including pytest-native admission, xdist/sharding, marker-based execution or separating evidence benchmarks from correctness checks) can change a frozen assurance contract and overlaps the active Python test-runner migration.

Therefore Stage D is **not auto-executable** under this plan. It stops at `CIPR-G4-SUITE-TOPOLOGY` with exact evidence and a recommended option after the Python test-runner migration reaches an appropriate stable gate. Until then, the canonical complete-suite command remains unchanged.

## 3. Work packets

### `CIPR-WP0` — bootstrap and authority freeze

Outputs:
- this plan;
- operator-instruction record;
- programme state;
- explicit frozen constraints and rollback.

Gate `CIPR-G0`: satisfied by the operator's explicit instruction to construct and execute this remediation, limited to the non-reserved Stage A-C envelope above.

### `CIPR-WP1` — integration-lane wait relocation

Outputs:
- non-serial canonical-test observer job;
- final merge-readiness dependency on observer success;
- no polling inside `ovc-main-integration-lane-v1`;
- stable-main and exact-head checks retained;
- regression tests.

Acceptance:
- exactly two PR workflow listeners remain;
- per-PR cancellation remains;
- canonical `tests` workflow is unchanged in this packet;
- observer has no global integration concurrency;
- merge-readiness retains global non-cancelling concurrency;
- merge-readiness contains no wait loop;
- base movement before/during readiness fails closed;
- exact-head repository and tiered checks pass.

Gate `CIPR-G1`: AUTO-RATIFIABLE if acceptance and QA pass and no unresolved review remains.

### `CIPR-WP2` — structured latency metrics

Outputs:
- structured metric lines for observation wait and final lane evaluation;
- deterministic regression assertions that metrics exist at the correct stages.

Gate `CIPR-G2`: AUTO-RATIFIABLE with WP1 when exact-head checks pass.

### `CIPR-WP3` — workflow inventory governance

Outputs:
- non-destructive classification registry/census for active workflow definitions;
- temporary/historical/manual/current-PR categories;
- no workflow deletion.

Gate `CIPR-G3`: AUTO-RATIFIABLE if classification is deterministic and authority delta remains NONE.

### `CIPR-WP4` — heavyweight-suite redesign decision packet

Outputs:
- measured heavy-test inventory refreshed on then-current main;
- compatibility assessment against the Python test-runner migration;
- alternatives: pytest parallelism, deterministic shard union, or governed benchmark separation;
- exact assurance invariants and rollback;
- recommended option.

Gate `CIPR-G4-SUITE-TOPOLOGY`: **OPERATOR REQUIRED** before any material change to the canonical complete-suite topology, runner admission boundary or frozen test-assurance contract.

## 4. Branch discipline

- WP0-WP2 are one approved grouped infrastructure packet because they implement one inseparable readiness-latency correction and do not change canonical test content.
- Initial branch: `build/ci-performance-remediation-v0-1` from exact baseline main above.
- Before every eligible merge, re-read current `main`, compare the packet base, classify movement using the existing PDC policy, reconcile when required, pin exact PR head, rerun required checks after any base-changing reconciliation, and never force-push.
- WP3 begins from lawful main after WP0-WP2 merge.
- WP4 may be prepared from then-current main but must stop at its operator-required gate.

## 5. QA and performance acceptance

Functional safety is mandatory; performance improvement is measured but must not be obtained by weakening assurance.

WP1-WP2 PASS requires:
- canonical complete repository suite PASS;
- OVC profile/tiered assurance PASS;
- no new PR listener;
- no duplicate complete-suite execution;
- global integration lane still present exactly once and only on final merge-readiness;
- canonical-test polling outside that lane;
- structured latency metrics present;
- zero blocking warnings/review threads.

Performance success criterion for Stage A is architectural: unrelated PRs must no longer wait in the global integration lane while another PR's canonical tests are merely in progress. The global lane may still serialize the short final evaluation itself.

## 6. Rollback

Rollback is non-destructive. Revert/supersede the Stage A workflow/test changes to restore the prior PDC v0.1 polling-inside-lane implementation while preserving this plan, QA, decision records and CI evidence. Do not delete historical workflows or test evidence as rollback.

## 7. Stop boundary

Continuous execution proceeds automatically through WP0-WP3 when all checks pass and authority delta remains non-reserved. Stop once `CIPR-G4-SUITE-TOPOLOGY` is ready because any material canonical-suite topology change is operator-reserved under the OVC continuous-development rules.

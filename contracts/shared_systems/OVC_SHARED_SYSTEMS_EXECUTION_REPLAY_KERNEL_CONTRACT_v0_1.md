# OVC Shared Systems Execution, Replay, Checkpoint and Capacity Kernel v0.1

Status: inactive/reference constitution under `SHSI-WP3`; authority effect `NONE`.

Meaning, logical computation, physical attempt and result evidence are separate:
`SemanticGenerationRef`, `RunSpecification`, `RunExecutionManifest` and
`ReplayResultManifest`. `ExecutionEnvironmentManifest`, host/path, worker count, chunk
size, shard order and backend never enter `LogicalResultIdentity`.

All identity-bearing population members are explicit and canonically ordered. Fresh,
resumed, re-sharded, cross-environment and physically reordered executions reconcile
only by exact logical result identity. A checkpoint binds the exact run specification,
committed canonical prefix and prefix hash. Corrupt, foreign or ambiguous checkpoints
fail closed; a committed item is never duplicated after restart.

Logical barriers are exact source/FVT facts, never elapsed wall-clock authority.
Capacity may change physical resources, partitioning or a qualified backend only. It
may not sample the population, reduce precision, suppress ambiguity, drop required
methods or change missingness. Insufficient capacity emits `CAPACITY_EXCEEDED` with no
logical result and a recovery receipt preserving the full specification.

The kernel executes synthetic/reference fixtures only. It grants no scientific run,
source, Validation, semantic, publication, probability, risk, exposure or execution
authority and is not wired to a current consumer.

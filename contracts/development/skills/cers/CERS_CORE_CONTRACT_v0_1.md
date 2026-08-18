# CERS Core Contract v0.1

Programme: `OVC-DSAI3V-CERS-CONFORMANCE-v0.1`.

CERS is an inactive/shadow liveness coordinator before `CERS-G-LIVE-DISPATCH`. Repository state and programme-owned authority remain controlling. CERS MUST NOT infer authority from branch names, PR text, workflow names, queue position, qualification, availability, chat state, or runnable status.

Required objects: `ReconciliationSnapshot`, `RunnableWorkItem`, `RunnableWorkSet`, `ExecutorCapabilityRecord`, `SupervisorLease`, `DispatchIdentity`, `DispatchTransaction`, `WorkerOwnership`, `QuiescenceControl`, `SupervisorCheckpoint`.

Unknown programme root or executor is non-dispatchable. Unknown action/side-effect is `IRREVERSIBLE_OR_UNKNOWN`. Unknown start becomes `UNKNOWN_START_STATE` and MUST be reconciled before any redispatch.

Supervisor fencing generations are monotonic. Every start, ownership transition, heartbeat and completion validates the current fence. Stale fence or stale worker completion is fatal.

Before the live gate only an executor proving `repository_write=false`, `branch_ref_write=false`, `merge=false`, `force_push=false`, and `irreversible_external_side_effects=false` may receive CERS dispatch.

`HOLD` and `DISABLE_NEW_DISPATCH` block new dispatch. `DRAIN` permits already-owned fixture work to finish but releases no successors.

CERS has no physical-main write path. `DSAI_VIT_PHYSICAL_CONTROLLER` through `DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY` remains exclusive; parallel physical merge remains false.

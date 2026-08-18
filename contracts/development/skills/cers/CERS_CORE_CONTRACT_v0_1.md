# CERS Core Contract v0.1

Programme: `OVC-DSAI3V-CERS-CONFORMANCE-v0.1`.

CERS is an inactive/shadow liveness coordinator before `CERS-G-LIVE-DISPATCH`. Repository state and programme-owned authority remain controlling. CERS MUST NOT infer authority from branch names, PR text, workflow names, queue position, qualification, availability, chat state, or runnable status.

## Required objects
`ReconciliationSnapshot`, `RunnableWorkItem`, `RunnableWorkSet`, `ExecutorCapabilityRecord`, `SupervisorLease`, `DispatchIdentity`, `DispatchTransaction`, `WorkerOwnership`, `QuiescenceControl`, `SupervisorCheckpoint`.

## Fail-closed rules
Unknown programme root => non-dispatchable. Unknown executor => non-dispatchable. Unknown action or side-effect class => `IRREVERSIBLE_OR_UNKNOWN` and non-dispatchable. Unknown start outcome => `UNKNOWN_START_STATE` / `DISPATCH_UNKNOWN`; reconcile observation before any redispatch.

## Fencing and ownership
Supervisor fencing generations are strictly monotonic per scope. Every start, ownership transition, heartbeat and completion must validate the current fence. A stale fence or stale worker completion is fatal qualification failure.

## Pre-activation executor boundary
Only a registered executor proving repository-write=false, branch/ref-write=false, merge=false, force-push=false and irreversible-external-side-effects=false may receive CERS fixture dispatch before the live gate.

## Quiescence
`HOLD` and `DISABLE_NEW_DISPATCH` block new dispatch. `DRAIN` permits existing owned fixture work to finish but releases no new successors. Operator/programme-owner quiescence dominates automated wake.

## Physical integration
CERS has no physical-main write path. `DSAI_VIT_PHYSICAL_CONTROLLER` through `DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY` remains exclusive; parallel physical merge remains false.

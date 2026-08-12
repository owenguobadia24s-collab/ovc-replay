# C2P Replay / Checkpoint / Projection Contract v0.2
Status: FROZEN_INACTIVE_CONFORMANCE / authority_effect=NONE

Clean replay, chunked replay, worker-count changes, checkpoint/restart and projection rebuild must preserve identity-bearing logical bytes.
Physical storage/chunk/worker/cache choices are non-identity operational metadata.
Indexes and read models are disposable/rebuildable. Capacity failure must fail closed or use only typed non-authoritative deferral allowed by the capacity tier contract.

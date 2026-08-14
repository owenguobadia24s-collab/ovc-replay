# OVC DSAI v0.3 Persistent Mandate & State Drainage Contract v0.1

Authority: development-execution state only. This contract grants no physical-main VIT authority and no programme-specific authority expansion.

`OVC RUN`, `OVC CONTINUE`, `RUN ONLY`, `CONTINUE ONLY`, `UNTIL` and `HOLD` are durable execution mandates. Accepted mandate scope, authority source, continuation policy and stop boundary must be recoverable without conversation state.

Each `DevelopmentLane` persists the current packet plus build, payload, VIT and materialisation frontiers. Recovery state persists active blockers, open recovery action, recovery-attempt count, wake subscriptions, open materialisation transaction reference and exact next packet.

`StateDrainageHarness` must load only repository/orchestration-backed durable bytes into a fresh process and reconstruct an equivalent `StateDrainageManifest`. Conversation text, assistant memory, worker identity and local transient process state are forbidden reconstruction dependencies.

Recoverable technical conditions remain `RECOVERING` while the bounded recovery budget is available. Authority-required transitions remain `WAITING_OPERATOR_AUTHORITY`; remediation may never erase or reinterpret them. Successful packet completion resolves `next_packet` immediately and may release the successor only when prerequisite and authority checks pass.

The runtime is prospective/inactive with respect to physical main. Parallel physical merge remains false.

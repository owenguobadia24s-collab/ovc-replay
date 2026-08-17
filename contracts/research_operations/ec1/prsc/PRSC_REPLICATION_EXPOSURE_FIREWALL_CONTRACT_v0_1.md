# PRSC Replication & Exposure Firewall Contract v0.1

## Scope
This contract governs PRSCI-WP7 synthetic replication planning and protected-source exposure controls. It creates no real replication, Development, Validation, CandidateFreeze, publication, probability, risk, exposure or execution authority.

## Replication constitution
- `ReplicationProtocolPack` binds one exact candidate/protocol generation, one source role, one disjointness rule and one transport rule.
- Default WP7 execution is synthetic only. `real_execution_allowed` MUST be false.
- A replication population must be proven disjoint under the declared identity unit before it may be described as replication evidence.
- Method transport is explicit: transported, refit, restricted and not-transportable states remain distinct.

## Exposure constitution
- Candidate-specific exposure is append-only and irreversible.
- HUMAN, ALGORITHM and SUMMARY exposure channels are tracked independently; once observed, a channel can never return to unexposed.
- Exposure cannot be erased by restart, cache rebuild, branch movement, protocol revision or failed review.
- Any protected Development/Validation reachability from the WP7 execution graph is blocking.

## Validation reservation
`ValidationReservationRecord` may reserve future capacity/identity only. It MUST contain no read path, locator, credential, query, provider selector, artifact handle or mechanism capable of consuming Validation evidence. State remains `RESERVED_UNCONSUMED`.

## Fail-closed conditions
Population overlap, exposure rollback, undeclared method refit, hidden protected-source reachability, real execution, or any Validation read surface is blocking.

## Preserved constraints
F0-A remains `HOLD`; Validation remains `LOCKED_UNCONSUMED`; CandidateFreeze remains `NONE`; real-source PRSC remains denied until `PRSCI-G-EC1-CHALLENGE`.

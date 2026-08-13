# C2P Event Ledger Contract v0.2
Status: FROZEN_INACTIVE_CONFORMANCE / authority_effect=NONE

The append-only `C2PEvent` ledger is the sole lifecycle/state-transition authority.
Events bind stream identity, sequence, prior-event hash, event type, effective chronology, FVT, cutoff, source/decision refs and canonical payload.
Conflicting payload at an existing logical event identity is an integrity failure and must quarantine; suffixing or mutation is forbidden.
Snapshots/read models are projections only.

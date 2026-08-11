# RCN-RN-WP4C — C2.5 Events Preparation Contract v1

Programme `OVC-RC-VNEXT-GREENFIELD-v0.1`; packet `RCN-RN-WP4C`; authority `AUTO_EXECUTABLE_PREPARATION_ONLY`.

Repository source census is binding: `OPT-B.C2.5` has no materialized runtime namespace and is `TYPED_DEGRADED_STATE` with reason `UPSTREAM_OWNER_NOT_MATERIALIZED_AS_RUNTIME_NAMESPACE`. WP4C MUST NOT fabricate temporal-event ASTs, event-calculus facts, lifecycle transitions, compiled state-machine events, or substitute C2E/C2 deltas for C2.5.

`GET /api/v1/c2-5/events` may expose only fixture-only typed absence: capability `C2_5`; owner `OPT-B.C2.5`; `availability=NOT_MATERIALIZED`; `runtime_owner_materialized=false`; `binding_state=PREPARED_NOT_BOUND`; empty `events`; reason code above; `event_synthesis=PROHIBITED`; `authority_effect=NONE`; `real_source_presentation=DENIED_PENDING_RCN_RN_G4`; gate `RCN-RN-G4`.

Validation MUST be denied before fixture resource resolution. Route remains GET-only. No C2.5 vocabulary/semantic activation, scientific inference, write path, Validation, probability/risk/exposure/trading/execution authority. First real-source presentation remains reserved to `RCN-RN-G4`.

PASS requires source-census consistency, empty deterministic typed absence, no synthesis/substitution, GET-only transport, full Research Console CI, QA PASS. Rollback removes this preparation surface only; G4 remains required.
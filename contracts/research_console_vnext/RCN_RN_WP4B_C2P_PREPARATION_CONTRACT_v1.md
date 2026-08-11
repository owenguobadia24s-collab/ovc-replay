# RCN-RN-WP4B — C2P Objects Preparation Contract v1

Programme `OVC-RC-VNEXT-GREENFIELD-v0.1`; packet `RCN-RN-WP4B`; authority `AUTO_EXECUTABLE_PREPARATION_ONLY`.

Repository census is binding: `OPT-B.C2P` has no materialized runtime namespace and is `TYPED_DEGRADED_STATE` with reason `UPSTREAM_OWNER_NOT_MATERIALIZED_AS_RUNTIME_NAMESPACE`. WP4B MUST NOT fabricate C2P/ObjectPack objects, memberships, lifecycle, eligibility, identity, or a runtime binding.

`GET /api/v1/c2p/objects` may expose only a fixture-only preparation envelope declaring: capability `C2P`; owner `OPT-B.C2P`; `availability=NOT_MATERIALIZED`; `runtime_owner_materialized=false`; `binding_state=PREPARED_NOT_BOUND`; empty `objects`; `reason_code=UPSTREAM_OWNER_NOT_MATERIALIZED_AS_RUNTIME_NAMESPACE`; `authority_effect=NONE`; and `real_source_presentation=DENIED_PENDING_RCN_RN_G4`.

Validation MUST be denied before fixture resource resolution. Route remains GET-only. No legacy/quarantine or market-grammar C2P parser artifacts may substitute for the persistent-object owner. No ObjectPack activation/promotion, scientific inference, write path, Validation, probability/risk/exposure/trading/execution authority. First real-source presentation remains reserved to `RCN-RN-G4`.

PASS requires deterministic typed absence, empty object population, source-census consistency, zero runtime-owner fabrication, GET-only transport, full Research Console CI, and QA PASS. Rollback removes this preparation surface only; G4 remains required.
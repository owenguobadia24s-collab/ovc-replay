# OVC SRFD Method Capacity Contract v0.2

Authority: `FIXTURE_LOCAL_CAPACITY_REMEDIATION_ONLY`  
Scientific effect: `NONE`

This contract governs SRFDI-G8R capacity scheduling only. It does not select, promote, disable or reinterpret a representation, distance, family method, sensitivity pack or family catalogue.

## Resource-contract identity

Each executable DAG node declares `node_id`, `node_type`, optional `method_id` and `configuration_id`, exact `dependency_ids`, `wall_seconds`, `peak_rss_bytes`, `external_bytes`, `measurement_class`, `reusable` and `required`.

`measurement_class` is one of `MEASURED`, `INTERPOLATED`, `EXTRAPOLATED`, `THEORETICAL_BOUND` or `UNRESOLVED`. Missing resource evidence is represented explicitly and yields `CAPACITY_UNRESOLVED`; it may not be replaced by zero or by an unstated estimate.

## Capacity status vocabulary

- `SUPPORTED_T0` — evidence supports the node inside T0.
- `SUPPORTED_T1` — evidence supports a non-method node inside T1 but not T0.
- `METHOD_CAPACITY_UNSUPPORTED_AT_T0` — an exact family method/configuration is outside T0 but remains present in the scientific DAG.
- `REQUIRES_SEPARATE_CAPACITY_TIER` — execution is outside T0 and T1.
- `CAPACITY_UNRESOLVED` — evidence is incomplete or a required backend is unadmitted.
- `CAPACITY_EXCEEDED_AT_MEASUREMENT` — a measured execution crossed a declared resource bound.

All statuses have `scientific_effect=NONE`.

## Completeness rule

The scheduler receives the complete preregistered set of required `(method_id, configuration_id)` pairs. Any missing or unexpected required method/configuration raises `CAP_METHOD_CONFIG_INCOMPLETE`. A capacity failure cannot be converted into a smaller scientific benchmark by orchestration.

`partial_benchmark_escape_hatch=PROHIBITED` and `scientific_scope_change_on_capacity_failure=PROHIBITED` are invariant.

## Dependency and ordering rule

All dependencies must resolve to declared nodes. Cycles fail closed. Deterministic topological ordering uses lexical `node_id` tie-breaking. Reusable shared distance/cache nodes may be executed once and referenced by multiple method nodes without changing logical experiment identity.

## Controlled failure

Unsupported/unresolved nodes emit a controlled capacity-failure record with action `STOP_NODE_PRESERVE_EVIDENCE_DO_NOT_DROP_METHOD`. The record grants no authority and does not satisfy a dependency.

## Planning tiers

T0 and T1 values remain provisional planning budgets until G8R-G6 accepts redesigned measurements. `SRFDI-G8-REPRESENTED` remains the separate operator decision that can freeze measured capacity and make parent WP9 eligible.

## Hard firewalls

WP9 `DENIED`; June `DENIED`; 2025 Validation `LOCKED_UNCONSUMED`; selector, method/family promotion, activation, publication, probability, risk, exposure and execution authority remain `NONE`. PR #371 remains `PRESERVE_DO_NOT_MERGE`.

# OVC MG EI-WP1 — Revised-C2 Source Adapter Contract v0.1

## Purpose

Define the only admissible read-only translation from a revised-C2 empirical state row into the existing market-grammar `C2LedgerInput` contract used by C2E. This packet replaces the MG-WP8 synthetic `c2_records` boundary at the implementation interface only. It does not yet claim an empirical population run; that occurs in EI-WP3.

## Authority

- programme: `OVC-MARKET-GRAMMAR-EMPIRICAL-INTEGRATION-JUNE-v0.1`
- packet: `EI-WP1`
- parent authority: operator `PASS` at `MG-WP10`
- authority state: inactive, noncanonical `SHADOW_EXPERIMENT`
- source: exact accepted June GBPUSD evidence only
- evaluation grain: `15M`, local frame, BID or ASK
- parent context clock: `2H_A_L` only
- writes: replaceable adapter records only

No selector, canonical selection, family/variant/rule/candidate/grammar/semantic promotion, C3 handoff, publication/new release identity, Active Discovery/Development/Validation, probability, risk, exposure or execution authority is granted.

## Accepted evidence binding

The adapter must be constructed with all three exact inherited identities:

- `binding_sha256 = 126a703b89bf8fc60a4beb1248b20b424621334c8fff254c122555e44663f8`
- `logical_population_sha256 = 3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7`
- `integrated_package_sha256 = 150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3`

and with `source_release_id = C2AR.INTEGRATED.SHADOW.PACKAGE.v1`. Any mismatch fails closed before a row is adapted.

## Revised-C2 empirical source row

The source row is a typed structural-state envelope. It is not an opportunity window, rule candidate, family assignment, outcome or semantic label.

Required fields:

- `record_id`
- `source_release_id`
- `instrument_id = GBPUSD`
- `side ∈ {BID, ASK}`
- `evaluation_scope_id = GBPUSD-15M-LOCAL-v0.1`
- `clock_id = 15M`
- `first_valid_time` — timezone-aware ISO-8601
- `axes` — all five axes: `LOCATION`, `MOTION`, `ORGANISATION`, `INTERACTION`, `QUALITY`
- `changed_axes` — zero or more of those five axes
- `source_sha256` — lowercase 64-character SHA-256 of the upstream revised-C2 record

Optional fields:

- `parent_context_record_id`
- `parent_clock_id` — when a parent is present it must equal `2H_A_L`
- `continuity_status`
- `reset_reason`
- `diagnostic_metadata` — diagnostic only and excluded from adapted identity/state semantics

Each axis contains `status`, nullable `value`, optional `reason_code`, and optional `measurement`. Measurements are retained upstream but never enter the C2E `state_key`; this prevents numeric over-fragmentation and preserves C2E as a categorical sequence operator.

## Axis status to C2E computability mapping

The adapter does not neutralise missingness. It maps the five axes by deterministic precedence:

1. any `QUARANTINED` → `QUARANTINED`
2. any `CONFLICT` → `CONFLICT`
3. any `CENSORED` → `CENSORED`
4. any `NOT_EVALUABLE` → `NOT_EVALUABLE`
5. any `NOT_EVALUATED` → `NOT_EVALUATED`
6. otherwise every axis must be `EVALUATED` → `EVALUABLE`

For every non-evaluable aggregate state, `not_evaluable_reason` is a deterministic sorted concatenation of axis name, status and explicit reason code. No implicit `NEUTRAL`, `BALANCED` or other substitute is permitted.

## C2E state key

The adapter constructs:

`LOCATION=<status>:<value>|MOTION=<status>:<value>|ORGANISATION=<status>:<value>|INTERACTION=<status>:<value>|QUALITY=<status>:<value>`

with axis order fixed as written. Null values are encoded as `NULL`. Measurements, source paths, machine names, user names and wall-clock/run metadata do not enter this key.

## Transition and reset mapping

- `changed_axes=[]` → `transition_kind=NONE`
- non-empty `changed_axes` → `transition_kind=AXIS_CHANGE`
- the adapter never invents `COMPLETION`, `TERMINATION` or semantic episode boundaries
- `reset_reason` is passed through only when `continuity_status` denotes a break/reset
- parent context is passed as `parent_record_id`; a changed 2H parent may therefore lawfully create a C2E parent-change boundary.

## Forbidden source content

Fail closed if any row contains any of:

`family_id`, `cluster_id`, `medoid_id`, `variant_id`, `sensitivity_pack_id`, `distance`, `grammar_id`, `parse_id`, `semantic_label`, `trade_label`, `outcome`, `outcome_id`, `return`, `returns`, `mfe`, `mae`, `future`, `future_price`, `future_path`, `probability`, `risk`, `exposure`, `execution`.

Unknown top-level fields also fail closed except the declared `diagnostic_metadata` envelope.

## Determinism

The same accepted row and binding must produce byte-identical adapted mappings regardless of input ordering, local path, machine name or diagnostic metadata. Batch output is sorted by `(first_valid_time, record_id)` and duplicate record IDs or timestamps within an exact side/scope are rejected.

## Rollback

Remove or supersede only the EI-WP1 adapter, schema, fixtures and compact evidence. Preserve EI-WP0, MG-WP10 and all accepted source bytes and hashes unchanged.

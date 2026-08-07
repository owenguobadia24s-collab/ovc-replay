# MCARB Auxiliary Evidence Contract v0.1

Programme: `OVC-MCARB-v0.1`  
Plan: `OVC-MCARB-IMPLEMENTATION-PLAN-0.1-REVISED`  
Packet: `MCARBI-WP2`

## Authority

This contract defines bounded research objects only. It grants no Stage-A market-run, provider-intake,
Validation, selector, C2/C2E/SRI/family/semantic, publication, probability, risk, exposure or execution authority.

## Domain boundary

`AL` is provider activity/liquidity evidence, not centralized FX traded volume or buyer/seller intent.
`ET` is an auxiliary intrinsic/event coordinate parallel to canonical clock time and cannot rewrite fixed observations.
`VS` is variation-scale evidence and remains distinct from C2 MOTION.

Every auxiliary record SHALL bind: `record_id`, `domain`, `candidate_id`, `instrument_id`, `side`,
`interval_start`, `interval_end`, `first_valid_time`, `admissible_cutoff`, `parent_ids`,
`calculation_version`, `variant_id`, `comparability_domain_id`, `missingness_state`, `value`, and `authority`.

Chronology invariant: `first_valid_time >= max(parent first_valid_time, own confirmation time)`.
Retrospective-only objects SHALL carry `RETROSPECTIVE_ONLY` and SHALL NOT enter causal packs.
Unknown or partial evidence is nullable and reason-coded; no interpolation, hidden imputation or zero-fill is lawful.

## AL source boundary frozen by MCARBI-G1

Source outcome: `AL_SOURCE_PARTIAL`.
Stage-A-eligible AL is limited to side-specific M1-derived provider activity candidates admitted by the
candidate registry. Provider-native H1 is not an exact AL parent. Cross-side interpretation, tick/update-count
claims and tick-truth spread claims remain unavailable unless separately superseded.

## Typed objects

The package defines:
`AuxiliaryMeasurement`, `AuxiliaryVariantSpec`, `AuxiliaryRepresentationPack`,
`AuxiliaryDependenceResult`, `AuxiliaryProxyQualityResult`, `MCARBCapacityReceipt`.
Later packets may implement deterministic constructors for these types but cannot expand their authority.

## Missingness states

`AVAILABLE`, `PARTIAL`, `NOT_EVALUABLE`, `SOURCE_FIELD_ABSENT`, `SOURCE_INTERVAL_GAP`,
`INSUFFICIENT_HISTORY`, `WARMUP_INCOMPLETE`, `SIDE_UNAVAILABLE`, `PARAMETER_NOT_APPLICABLE`,
`RETROSPECTIVE_ONLY`, `STALE`, `CONFLICT`, `QUARANTINED`.

Capability is not authority.

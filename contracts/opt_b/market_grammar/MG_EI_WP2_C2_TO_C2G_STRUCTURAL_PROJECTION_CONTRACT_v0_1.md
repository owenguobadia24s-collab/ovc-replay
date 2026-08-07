# OVC MG EI-WP2 — C2-to-C2G Structural Projection Contract v0.1

## Purpose

Replace the second MG-WP8 mocked boundary, `state_structural_features`, with a deterministic read-only projection from the exact revised-C2 source-row contract frozen at EI-WP1 into the already implemented C2G `StructuralRecord` contract.

This packet changes no sensitivity pack, metric, family algorithm, medoid rule, variant rule or hierarchy rule. The five feature keys are exactly the frozen C2G keys: `location`, `motion`, `organisation`, `interaction`, `quality`.

## Authority

- programme: `OVC-MARKET-GRAMMAR-EMPIRICAL-INTEGRATION-JUNE-v0.1`
- packet: `EI-WP2`
- parent: completed EI-WP1 and operator `MG-WP10 PASS`
- authority: inactive, noncanonical `SHADOW_EXPERIMENT`
- source scope: GBPUSD 15M BID/ASK with `2H_A_L` parent context only

No canonical sensitivity, family, variant, rule, candidate or grammar selection is authorised. No selector, C3, publication, active research, probability, risk, exposure or execution authority exists.

## Projection rule

The projection consumes the same EI-WP1 revised-C2 empirical source row and first validates it through the EI-WP1 adapter contract. It never consumes C2G family/assignment output, outcomes or future records.

For an `EVALUATED` source axis, `measurement` is the only admissible C2G coordinate. It must be a finite decimal in the closed interval `[0,1]`. No categorical rank, hash embedding, hidden threshold, learned embedding or runtime normalization is permitted.

When all five axes are `EVALUATED` and all five measurements are valid `[0,1]` decimals, the projected state record is `EVALUABLE` and contains exactly:

- `location`
- `motion`
- `organisation`
- `interaction`
- `quality`

with canonical 12-decimal quantization inherited from C2G.

If any source axis is not `EVALUATED`, or an evaluated axis has a missing/non-finite/out-of-range measurement, the projected state record is `NOT_EVALUABLE`, has an empty structural-feature map, and carries a deterministic reason. Partial coordinate vectors are prohibited because they would change effective feature weights and distance semantics.

## Identity and provenance separation

The projected `StructuralRecord` reuses the upstream revised-C2 `record_id`, `source_release_id`, instrument, side, scope, clock, first-valid time and `source_sha256`. Diagnostic metadata, source paths, provider names, manifest IDs, hashes and computability markers are forbidden as structural feature keys by C2G and are not copied into the feature map.

Batch logical identity is computed over canonical projected output after sorting by `(side, first_valid_time, record_id)`; source order and diagnostic metadata cannot change it.

## Frozen C2G dependency

The projection is compatible with `MG-C2G-SENSITIVITY-PACK-REGISTRY-v0.1`, whose five packs all use equal weights over exactly the five feature keys above and all remain `canonical=false`, `comparison_only=true`. EI-WP2 may not edit that registry.

## Population claim

EI-WP2 proves the real projection implementation boundary with contracts and deterministic fixtures. It does not claim that the accepted June empirical population has yet supplied valid normalized measurements for all five axes. That is tested by EI-WP3. A population-wide measurement incompatibility is evidence, not permission to alter the projection contract silently.

## Rollback

Remove or supersede only the EI-WP2 projection artifacts. Preserve EI-WP1, EI-WP0, MG-WP10, frozen C2G sensitivity packs and accepted source evidence unchanged.

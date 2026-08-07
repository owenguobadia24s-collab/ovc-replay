# MG-WP9 Read-Only Review Surface Contract v0.1

**Programme:** `OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1`  
**Packet:** `MG-WP9`  
**Authority:** inactive, noncanonical `SHADOW_EXPERIMENT` read-only review only.

## Purpose

Expose the completed market-grammar evidence through one deterministic typed read model without granting mutation, promotion, selector, publication or semantic authority.

The review model must make the underlying evidence easier to inspect while never outranking or rewriting its source records. Raw registries, contracts, fixtures, QA and decision records remain the court record.

## Required review surfaces

The model exposes typed sections for:

- sensitivity comparison across the frozen comparison packs;
- family hierarchy, overlap, split and merge evidence;
- family and variant medoids plus stability metrics;
- assignment explanations and nearest family/variant distances;
- typed grammar AST and parser trace;
- 15M / 2H_A_L context availability and missingness;
- all fourteen CEAR-G10 candidate migrations;
- counterexample ledger;
- issue/warning ledger;
- source and authority bindings.

## Input authority

WP9 consumes only completed read-only evidence already admitted by the programme:

- the MG-WP8 topology fixture and deterministic smoke builder;
- the frozen C2G sensitivity-pack registry;
- the MG-WP7 migration ledger and its fourteen compact migration records;
- the MG-WP8 completed decision/QA state.

WP9 may rebuild a derived review model from those sources. It may not mutate any input or introduce a new market observation, family, variant, grammar, threshold or candidate.

## Read-model guarantees

1. `mutation_controls=false` and every section is `READ_ONLY`.
2. No sensitivity pack, family, variant, grammar or candidate is marked canonical.
3. Provenance remains diagnostic only and is never a structural match feature.
4. Missing/stale/not-evaluable context remains explicit.
5. Every candidate surface retains source IDs, migration status, source hashes and counterexample identity/count.
6. Grammar review exposes the exact frozen AST, release hash, parse status, missing/conflicting evidence and upstream lineage.
7. Issue and counterexample surfaces retain negative evidence; they cannot be filtered out of the canonical review-model identity.
8. Same source bytes produce the same review-model SHA-256 regardless of local path, machine name, input candidate order or JSON object insertion order.
9. Derived indexes are replaceable. Deleting and rebuilding the review model loses no authority.

## Prohibited controls

No review-model field or adapter may provide:

- threshold or sensitivity write/proposal control;
- selector activation/replacement;
- family/variant/rule/grammar/candidate promotion;
- canonical selection;
- C3 semantic handoff;
- publication or new immutable release identity;
- Active Discovery, Development or Validation;
- probability, eligibility, risk, exposure, trading or execution authority.

## Rollback

Remove or supersede the WP9 review-model implementation and derived compact surfaces. Preserve all WP1-WP8 raw evidence, decisions and source hashes unchanged.

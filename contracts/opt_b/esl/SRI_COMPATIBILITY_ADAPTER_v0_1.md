# OPT-B ESL SRI Compatibility Adapter Contract v0.1

Programme: `OVC-OPTB-ESL-CONFORMANCE-v0.1`  
Packet/Gate: `ESLI-WP5 / ESLI-G5`  
Plan: `OVC-OPTB-ESL-CONFORMANCE-IMPLEMENTATION-PLAN-0.1-REVISED-2`  
Authority: `INACTIVE_CONFORMANCE_ONLY`; authority delta `NONE`.

## Purpose

This contract makes the completed SRI/SFC representation surface a lawful reader of frozen `StructuralOccurrenceRecord` objects without changing StructuralOccurrence identity, selecting a scientific representation, activating a family/topology, or rewriting historical SRFD/SFC evidence.

`StructuralOccurrenceRecord -> SRICompatibilityPack -> SRICompatibilityRecord`

The adapter is a method-neutral projection boundary. It is not a replacement representation algorithm. Existing SFC/SRFD representation implementations remain separately addressable and retain their historical identities.

## Mandatory rules

1. **Immutable source.** The adapter consumes one exact `occurrence_record_id`, `occurrence_pack_id`, EvidenceFrontier, source generations, first-valid time and evaluation cutoff. It never repairs or mutates the occurrence or its upstream C2/C2P/C2E truth.
2. **Pack-declared exposure.** Every bootstrap structural dimension is explicitly either exposed or omitted. A dimension cannot be both. No undeclared source field may enter the representation.
3. **Explicit information loss.** Every omitted dimension must be declared in `information_loss_dimensions`. Silent loss, zero fill, mean fill, carry-forward and imputation are prohibited.
4. **Facet preservation.** Exposed facet evidence state, source references, raw value and reason codes are copied losslessly into `structural_raw`. WP5 performs no numeric feature extraction, normalization, embedding or scalarisation.
5. **Namespace separation.** WP5 leaves `structural_derived`, `structural_normalized` and `comparison_only` empty. Later lawful SRI packs may populate them under separately declared transforms; WP5 does not select such transforms.
6. **Context firewall.** Context may enter only when the exact pack names every context field and declares role `REPRESENTATION_INPUT`. Undeclared context or another role fails closed.
7. **Comparability binding.** The representation binds the exact source comparability domain and an explicit comparability generation. Domain mismatch fails closed; a generation change changes representation identity and never rewrites the predecessor.
8. **Chronology/provenance.** The exact source FVT, evaluation cutoff, EvidenceFrontier logical hash and source generations are identity-bearing provenance. No hindsight is introduced.
9. **Historical addressability, not identity.** `SRI-R1…R9`, current SFC `SRI-R1…R9`, and historical `SRFDI-R1…R9` may be crosswalked as semantic/naming aliases only where the frozen crosswalk says so. Crosswalks never assert record-ID equality, replay replacement or scientific promotion.
10. **Leakage rejection.** Family/prototype/distance/similarity, outcome/Validation, probability/risk/exposure/trading/execution and future-performance fields are forbidden recursively in source or context input.
11. **No scientific selection.** The only WP5 method is `METHOD_NEUTRAL_IDENTITY_PROJECTION_v0_1`. Supplying another method ID fails closed. Representation, normalization, topology, family and method selection remain deferred.
12. **No activation.** Every output records `representation_activation=NONE`, `method_selection=NONE`, `family_promotion=NONE`, `semantic_promotion=NONE`, and `validation_consumption=LOCKED_UNCONSUMED`.

## Compatibility identity

`representation_id = "sri1:" + SHA256(canonical-json-v1(identity payload))`.

The identity payload includes the exact pack/version, declared class, source population ID, exact source occurrence provenance, exposed raw facets, explicit missingness/omissions/information loss, context binding, comparability domain/generation, historical alias references and authority boundary. It excludes only the record's own `representation_id` and `logical_hash` because they are appended after hashing.

## Historical crosswalk

`registries/opt_b/esl/SRI_HISTORICAL_CROSSWALK_v0_1.json` is descriptive compatibility evidence. It keeps historical SFC/SRFD namespaces addressable. It does not rename files, rewrite IDs, reinterpret historical outputs, or grant any current selector/representation/family authority.

## Failure policy

Ambiguous or undeclared source use fails closed with an `ESL_SRI_*` reason. A lawful base StructuralOccurrence remains lawful if an SRI projection cannot be formed. WP5 failure cannot poison the base structural statement.

## Rollback

Rollback is forward-only: remove/supersede the WP5 compatibility adapter, manifest/schema/fixture and records while preserving all historical SFC/SRFD artifacts and ESL WP0–WP4 evidence. No data migration, source rewrite, selector change, force-push or history rewrite is required.

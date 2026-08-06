# MG Predicate Domain, Exclusivity and Component Classification Contract v0.1

**Contract ID:** `MG-PREDICATE-DOMAIN-EXCLUSIVITY-CLASSIFIER-0.1`  
**Programme:** `OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1`  
**Packet:** `MG-WP1`  
**Authority:** inactive, noncanonical `SHADOW_EXPERIMENT` computation only

## 1. Purpose

Separate market structure from timing, object binding, context, computability and provenance before any family or grammar construction. Correct the legacy practice in which a high-frequency non-common value could be called `CONTRADICTORY` without a logical proof.

## 2. Typed domains

Every component has exactly one declared domain:

- `STRUCTURAL` — observable market organisation or relation content;
- `TEMPORAL` — order, duration and first-valid chronology;
- `OBJECT_BINDING` — typed links among levels, relations, states, episodes and parse nodes;
- `CONTEXT` — instrument, clock, session or parent-context applicability;
- `COMPUTABILITY` — missingness, censoring, staleness and evaluability;
- `PROVENANCE` — release, manifest, provider, record, commit and content identity.

Source release IDs, manifest IDs, record IDs, provider names, hashes and equivalent lineage fields are never structural predicates. Clock identity is context, not market structure. Computability status is applicability evidence, not neutrality.

## 3. Component statistics

A `ComponentStats` record binds one feature to one exact object scope, clock and first-valid time. Counts must be non-negative and satisfy:

```text
present_count + missing_count <= total_eligible
absent_count = total_eligible - present_count - missing_count
```

A statistics record spanning multiple clocks, object scopes or first-valid times is invalid and must be split before classification.

## 4. Classification vocabulary

The only allowed classes are:

- `INVARIANT`
- `COMMON`
- `NORMAL_VARIATION`
- `HIGH_CARDINALITY_VARIATION`
- `MISSINGNESS_VARIATION`
- `LOGICAL_CONFLICT`
- `OPTIONAL`
- `RARE`

Classification is deterministic under the frozen classifier implementation and registry versions.

## 5. Logical conflict proof

Frequency, rarity, entropy, cardinality or disagreement alone never proves logical conflict. `LOGICAL_CONFLICT` requires all of:

1. a versioned exclusivity rule;
2. the same feature key and typed domain;
3. the same exact object scope;
4. `clock_scope=SAME_CLOCK`;
5. `time_scope=EXACT_FIRST_VALID_TIME`;
6. at least two observed values contained in the rule's mutually-exclusive value set.

Wildcard scopes are prohibited. Provenance and computability fields may not define logical conflict.

## 6. Deterministic classification order

1. A single value present in every eligible record with no missingness is `INVARIANT`.
2. A valid exact-scope exclusivity proof is `LOGICAL_CONFLICT`.
3. Coexisting present and explicitly missing observations are `MISSINGNESS_VARIATION`.
4. Eight or more distinct values, or a distinct-to-present ratio of at least 0.5 with at least eight present observations, is `HIGH_CARDINALITY_VARIATION`.
5. More than one observed value without exclusivity proof is `NORMAL_VARIATION`.
6. A single value with present ratio at least 0.7 is `COMMON`.
7. A single value with present ratio at least 0.2 is `OPTIONAL`.
8. Remaining cases are `RARE`.

Thresholds in this contract are classifier mechanics for the inactive experiment and are not market selectors, family sensitivities or activation thresholds.

## 7. Legacy migration

Legacy `CONTRADICTORY` has no direct mapping. Every legacy component is recomputed from typed statistics and the exact exclusivity registry. A migrated component records its legacy class, new class, domain, structural eligibility and reason. Historical records remain unchanged.

## 8. Authority and prohibitions

This contract authorises schemas, registries, fixtures, deterministic code, migration adapters and tests inside MG-WP1. It does not authorise:

- selector activation;
- canonical predicate, sensitivity, family, variant or grammar release;
- rule or semantic promotion;
- C3 handoff;
- publication or Validation consumption;
- probability, risk, exposure or execution.

## 9. Acceptance

MG-WP1 passes only when:

- all six domains and eight classes are schema- and registry-bound;
- reserved provenance/context/computability fields cannot be declared structural;
- exact-scope exclusivity is required for `LOGICAL_CONFLICT`;
- invalid/wildcard scopes are rejected;
- legacy `CONTRADICTORY` is recomputed rather than copied;
- fixtures cover invariant, common, normal variation, high cardinality, missingness, logical conflict, optional, rare and invalid cases;
- deterministic focused and complete repository tests pass;
- QA records no reserved authority delta.

## 10. Rollback

Remove or supersede the inactive implementation while preserving this contract, fixtures, QA and decisions. Never relabel historical components in place or weaken exclusivity requirements to obtain a passing result.

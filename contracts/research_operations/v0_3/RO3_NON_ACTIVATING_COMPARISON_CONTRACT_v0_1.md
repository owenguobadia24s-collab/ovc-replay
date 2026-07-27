# RO3 Non-Activating Comparison Contract v0.1

Status: `FROZEN_AT_RO3_G0`

Every C1 formula, contract, schema or release comparison is evidence only.

## Required sequence

1. Validate explicit role, source identity, comparison class, registry/contract/schema identities and source population.
2. Create a deterministic comparison ID.
3. Return only the `NON_ACTIVATING_EVIDENCE_HEADER`.
4. Require an append-only Research Operations AuditEvent with event type `NON_ACTIVATING_COMPARISON_ACKNOWLEDGEMENT`.
5. Bind the acknowledgement to operator ID, comparison ID, exact base/target hashes, exact boundary statement and timestamp.
6. Reveal the detailed diff only when the acknowledgement is exact, current and matching.

## Mandatory header

```json
{
  "authority": "NON_ACTIVATING_EVIDENCE_ONLY",
  "formula_change_authority": "NONE",
  "release_change_authority": "NONE",
  "selector_change_authority": "NONE",
  "required_next_process": "SEPARATE_IMPLEMENTATION_PLAN_AND_OPERATOR_GATE"
}
```

## Allowed comparison classes

`IDENTICAL_DEFINITION`, `CONTRACT_CHANGED`, `FORMULA_CHANGED`, `DOMAIN_CHANGED`, `NULL_POLICY_CHANGED`, `CHRONOLOGY_CHANGED`, `SYMMETRY_CHANGED`, `SERIALIZATION_CHANGED`, `POPULATION_CHANGED`, `OUTPUT_CHANGED`, `NOT_COMPARABLE`.

Discovery and Development may be contrasted only as `ROLE_CONTRAST`; they are not equivalent populations. Validation content is denied before resolution.

## Prohibited outputs

A comparison must not choose, rank, recommend or activate a winner; propose a threshold; rewrite a historical record; mutate a registry, contract, schema, release or selector; or use language such as preferred, superior, fix, tune, promote or activate.

`activation_recommendation` is always `null`.

## Failure behavior

Missing, stale, reused or mismatched acknowledgement returns the header and `ACKNOWLEDGEMENT_REQUIRED` or `ACKNOWLEDGEMENT_MISMATCH`; no detailed diff is disclosed.

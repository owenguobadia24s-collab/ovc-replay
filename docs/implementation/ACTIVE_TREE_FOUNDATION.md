# Active-tree foundation

The active tree separates infrastructure, governance and future implementation namespaces from historical ABCD machinery.

## Dependency direction

```text
provider evidence -> OPT-A v2 -> C1 v2 -> C2 v2 -> later evidence-gated layers
```

Reverse reads are prohibited. The package skeletons contain no market logic and no active selectors.

## Storage planes

- Git: contracts, schemas, registries, compact fixtures, code, tests and decisions.
- Local external root: candidate payloads and generated streams.
- R2 canonical: immutable, verified release bytes.

## Historical boundary

The frozen baseline and release records remain auditable. The quarantined engine may be used only for historical audit, source crosswalk and bounded defect-fixture derivation.

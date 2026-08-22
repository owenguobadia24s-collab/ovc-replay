# SHSI-WP1 — Bootstrap and Identity Constitution

Plan: `OVC-SHARED-SYSTEMS-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-R1`  
Gate: `SHSI-G1`  
Baseline main: `18827c2c1eff4bedcba7717c2c1a7ecf935cde45`  
Authority: `AUTO_EXECUTABLE_WITHIN_SHSI-AE-v0.2-R1`; delta `NONE`.

## Prerequisite closure

SHSI-G0B is complete at the exact WP0 merge commit/tree. Its detached exact-head
qualification, repository-wide assurance and canonical four-receipt physical completion
bundle are bound by `SHSI_G0B_COMPLETION_BINDING_v0_1.json`.

## Materialised

- strict `SerializationProfile`, `IdentityProjection` and
  `LegacySerializationBinding` contracts and schemas;
- independent hash/profile/projection/legacy registries;
- standard-library-only deterministic reference canonicalizer and profile-bound logical
  identity implementation;
- separately coded comparator, frozen golden vectors and serializer-collision fixture;
- exact-context legacy lookup that returns the stored historical digest without rehash;
- fail-closed unknown, ambiguous, non-NFC, negative-zero, missing-field and registry
  collision paths;
- explicit logical-content, profile-bound logical identity and physical-blob digest
  separation;
- current implementation reuse census with existing consumer paths unchanged.

No Shared Systems runtime is active. No consumer path, domain truth, historical ID,
source/provider role, scientific/semantic state, Validation, publication, exposure or
execution authority changes.

## Rollback

Before merge, preserve/close this branch. After merge, correct forward through a new
profile/projection/binding generation; retain Stage-0 and historical identities.

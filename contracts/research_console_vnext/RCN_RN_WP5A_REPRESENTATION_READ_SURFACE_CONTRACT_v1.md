# RCN-RN-WP5A Representation Read Surface Contract v1

Status: IMPLEMENTATION CONTRACT  
Programme: `OVC-RC-VNEXT-GREENFIELD-v0.1`  
Plan: `OVC-RCN-RESEARCH-NATIVE-IMPLEMENTATION-PLAN-0.3-RATIFIED`  
Packet: `RCN-RN-WP5A`  
Authority effect: `NONE`

## 1. Purpose and source boundary

This contract implements the WP5A Research representation surface for SRI, FDI, SRFD and MCARB as a bounded GET/read-only, synthetic-fixture, non-evidentiary projection.

The source set is frozen by `wp5a_representation_source_bindings_v1.json`. Every source must be repository-addressable, carry its declared fixture-only authority marker, and match its exact Git blob identity before presentation. The surface does not read provider data, Validation data, real Research outputs, or any first-new real Research source.

## 2. Authority preflight

The no-new-source branch `RCN-RN-WP5A-CLOSEOUT` is eligible only when all sources are synthetic/fixture-only or otherwise already authorised for the exact presentation surface. This implementation uses fixture-only sources exclusively.

Any source classified as real, provider-backed, Validation, authoritative scientific output, or first-new real Research exposure is a hard authority failure. It must route to `RCN-RN-G5-FIRST-NEW-SOURCE` and may not be exposed before an explicit operator decision.

Existing G4 MARKET/C1/C2/C2E Investigate authority is not transitive to WP5A.

## 3. Scientific firewalls

The surface is method-first, not family-first. It preserves source-owned identities and evidence without selecting or promoting a representation, distance, method, topology, family, sensitivity result, candidate or theory.

The following are mandatory:

- every `winner` and `default_winner` field is null;
- selector authority is `NONE`;
- frontend scientific calculation is `PROHIBITED`;
- correspondence is descriptive and is not independence;
- residual, ambiguity and `NO_STABLE_FAMILY` are equally lawful terminal outcomes;
- no forced family assignment or hidden winner score is permitted;
- missing or incompatible evidence remains typed and visible;
- downstream presentation cannot repair, infer or synthesize missing source facts.

## 4. Transport and protected-data boundary

All WP5A endpoints are GET/read-only. POST, PUT, PATCH and DELETE remain denied by the application boundary.

A `role=VALIDATION` request is denied before fixture or source resolution. Validation identity, path, timestamp, count and payload remain locked and unconsumed.

The WP5A route remains explicitly fixture-only even when the separate Investigate source mode is `REAL`; it never falls back from a failed real Research source because no real Research source is bound.

## 5. Determinism, identity and capacity

The service verifies Git blob identities using Git's canonical `blob <length>\0<bytes>` SHA-1 object identity. Source order, fixture order and object iteration may not change the returned logical content.

Population and outcome denominators must reconcile exactly. Truncation, absence and capacity states must be explicit; silent sampling or record loss is prohibited.

## 6. UI inheritance

The React surface reuses the v0.3 production WorkbenchFrame shell: global domain rail, application header, context/authority strip, workbench navigator, analytical canvas, evidence inspector, evidence dock and status bar.

The UI renders source-provided values only. It may format and order those values but may not derive a scientific score, rank, winner, family assignment or sensitivity conclusion.

## 7. Acceptance

WP5A may close only when:

1. source identities and fixture-only authority markers verify;
2. no first-new real Research source is exposed;
3. method-first, null-winner and equal-status outcome invariants pass;
4. Validation denies before source reads;
5. API, schema, client and React surfaces agree;
6. targeted, Research Console and repository-wide assurance pass;
7. QA recommends PASS with authority delta `NONE`;
8. rollback is reproducible and no blocking warning or review remains.

## 8. Rollback

Disable or revert only the WP5A route, fixture projection, client/component, bindings and packet evidence. Preserve the ratified plan, governing PPM, G4 decision, completed post-G4 binding, source fixtures and Git history. Rollback never activates another source, unlocks Validation, changes a scientific selector, or performs a force-push/history rewrite.

# OVC C2E–C2G–C2P Integrated Market-Grammar Implementation Plan v0.1

**Plan ID:** `OVC-C2E-C2G-C2P-INTEGRATED-MARKET-GRAMMAR-IMPLEMENTATION`  
**Programme:** `OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1`  
**Baseline:** main `372b072959863957d80c4dc12f393ae97bba482e`  
**Mode:** inactive, noncanonical `SHADOW_EXPERIMENT`  
**Terminal authority:** operator-required

## 1. Scope and authority

This plan implements the design specification in bounded packets. It permits repository
contracts, schemas, registries, fixtures, deterministic algorithms, local/read-only
adapters, tests, QA, compact evidence and inactive shadow outputs.

It does not permit:

- active selector creation or replacement;
- a canonical sensitivity pack, family hierarchy or variant taxonomy;
- rule or grammar promotion;
- C2E/C2G/C2P authoritative consumption;
- active C2 or C2.5 contract mutation;
- C3 semantic handoff;
- canonical/R2 publication;
- Active Discovery, Development or Validation;
- outcomes in construction;
- probability, eligibility, risk, exposure or execution authority.

## 2. Preconditions

MG-WP0 must bind and independently validate:

- current main and open-PR state;
- C2AR G10/G11 decisions and merge receipts;
- the accepted source slice and four source-object hashes;
- replay binding, code commit and repository inventory;
- two clean run manifests plus restart manifest;
- determinism, restart, preflight and capacity receipts;
- integrated package ID/hash and final QA;
- current programme registry and the prior C2E block.

Any mismatch becomes `BLOCKED` or `QUARANTINED`; no substitute or chat-only evidence is
accepted.

## 3. Packet sequence

### MG-WP0 — Baseline, evidence binding and implementation registry

Outputs:

- verified shadow-evidence lock;
- immutable operator supersession record for the prior C2E block, limited to this plan;
- programme state and implementation registry;
- external artifact inventory;
- design and plan documents;
- D8 delegated PASS.

Gate `MG-G0` is auto-ratifiable if no mismatch or reserved delta exists.

### MG-WP1 — Predicate domains and exclusivity

Build:

- predicate-domain contract and schema;
- exclusivity registry;
- classifier implementing `INVARIANT`, `COMMON`, `NORMAL_VARIATION`,
  `HIGH_CARDINALITY_VARIATION`, `MISSINGNESS_VARIATION`, `LOGICAL_CONFLICT`,
  `OPTIONAL`, `RARE`;
- structural/provenance ablation fixtures;
- migration adapter for old frequency classifications.

Acceptance:

- frequency alone never emits `LOGICAL_CONFLICT`;
- source IDs/hashes/clock IDs cannot become structural clauses;
- invalid exclusivity scope is rejected.

### MG-WP2 — C2E ledger

Build:

- episode/phase/interruption/completion/censoring contracts and schemas;
- deterministic boundary policy;
- nesting and object-binding ledger;
- explicit ambiguity and not-evaluable states;
- valid/invalid fixtures and chronology tests.

Acceptance:

- no C2G input;
- same ordered C2 input and pack yields same IDs;
- future records and outcomes are rejected.

### MG-WP3 — C2G sensitivity and hierarchy

Build:

- C2G-S sensitivity packs for 0.20, 0.35, 0.50 and lawful adjacent values;
- deterministic distance and assignment;
- C2G-H overlap/hierarchy DAG;
- split, merge, overlap, persistence, dispersion and survival measures.

Acceptance:

- no pack becomes canonical;
- directional graph is acyclic;
- unordered iteration cannot alter nodes/edges/assignments.

### MG-WP4 — Variants and residuals

Build:

- C2G-V FamilyVariant discovery;
- real family and variant medoids;
- stability, ambiguity, residual, unassigned and counterexample ledgers;
- explanation records for every assignment.

Acceptance:

- medoid is always a real member;
- variant is stable under its declared pack criteria;
- every unassigned member has a reason.

### MG-WP5 — Clock profiles and alignment

Build:

- 15M evaluation / 2H_A_L context profile;
- as-of resolver;
- stale/unavailable/not-evaluable states;
- multi-clock lineage and parent-child fixtures.

Acceptance:

- `parent_first_valid_time <= child_first_valid_time`;
- missing context never becomes neutrality;
- cross-side/release/profile parentage fails closed.

### MG-WP6 — C2P typed AST, compiler and parser

Build:

- typed AST and schema;
- compiler for required operators;
- immutable candidate grammar release;
- deterministic parser and result schema;
- invalid operator/type fixtures.

Acceptance:

- operator inputs are type checked;
- grammar release hash is immutable;
- parser retains all required lineage and evidence fields.

### MG-WP7 — Fourteen-candidate migration and ablation

For each CEAR-G10 rule candidate, record:

- source candidate and functional-core IDs;
- old component classifications;
- domain separation;
- typed grammar mapping;
- `MAPPED`, `SUPERSEDED`, `QUARANTINED` or `UNRESOLVED`;
- frequency-conjunction versus typed-grammar comparison;
- provenance-inclusive ablation;
- counterexamples and conflict proof status.

No candidate is promoted.

### MG-WP8 — Full real-component topology smoke

Run:

```text
revised C2
 -> C2E
 -> C2G state/transition family
 -> hierarchy/variant
 -> episode grammar
 -> immutable grammar fixture
 -> C2P parse
 -> read-only projection
```

Use accepted read-only evidence where reproducible and bounded fixtures where the prior
package explicitly lacks a real intermediate record. Every mocked boundary is named.
Two clean runs and checkpoint/restart are required for retained bulk outputs.

### MG-WP9 — Read-only review surfaces

Build typed read-model objects for:

- sensitivity comparison;
- family graph and variants;
- medoid/variant stability;
- assignment explanation;
- grammar AST and parse trace;
- 15M/2H context status;
- fourteen-candidate migration;
- issue and counterexample ledgers.

No mutation controls.

### MG-WP10 — Consolidated terminal decision

Prepare one operator-required packet for any proposed authority delta. The packet must
contain baseline/candidate commits, packet completion, current authority, proposed delta,
tests, QA, warnings, unresolved cases, changed files, external hashes, sensitivity and
grammar evidence, rollback and exact continuation.

Allowed decisions: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE`, `SUPERSEDE`.

## 4. Required comparison matrix

- sensitivities 0.20, 0.35, 0.50 plus lawful adjacent values;
- split, merge and partial overlap;
- medoid and variant-medoid stability;
- structural-only and provenance-inclusive diagnostics;
- old frequency-conjunction and typed grammar;
- C2-only, C2+C2E, C2+C2G and full chain;
- assigned, ambiguous, residual and unassigned;
- counterexamples and logical conflicts;
- 15M-only and lawful 15M-with-2H-context.

## 5. Test programme

Every packet receives:

- schema validation;
- valid and invalid fixtures;
- exact identity tests;
- chronology and leakage tests;
- randomized input-order tests;
- path/machine independence tests;
- targeted packet tests;
- complete repository tests;
- FINAL_HEAD and merge readiness;
- external artifact inventory/hash checks;
- rollback record.

## 6. Branch and merge discipline

Use one branch per packet or explicitly approved grouped packet. Begin every permanent
packet from the latest lawful main. Auto-ratify only wholly auto-executable PASS gates.
Pin PR head, rerun checks after base movement and squash-merge. Never force-push.

## 7. Stop conditions

Stop at:

- any proposed activation/canonisation/promotion/publication/selector/C3 handoff;
- missing or changed accepted evidence;
- an uncorrectable test, chronology, leakage, identity or capacity defect;
- governing-document conflict;
- scope expansion;
- terminal MG-WP10 operator decision.

# OVC MCAC Conformance Implementation Plan v0.1

Programme: `OVC-MCAC-v0.1`  
Capability: `OVC.MCAC.INACTIVE.DESCRIPTIVE.UTILITY.v0.1`  
Design input: `OVC Multiclock Coordinate, Alignment and Correspondence Design Specification v0.1 Revised 1`  
Status: `FROZEN_REVIEW_CANDIDATE`

## 1. Purpose and authority envelope

This plan materialises the reviewed MCAC design as a small repository-native Research Operations capability. It implements deterministic, read-only, clock-explicit comparison machinery and preserves historical negative doctrine. It creates no clock, source, market, scientific selector, phase/state ontology, probability, validation, publication, risk, exposure, trading or execution authority. The capability remains `INACTIVE`; Validation remains `LOCKED_UNCONSUMED`.

The operator mandate `OVC RUN MULTICLOCK-COORDINATE-ALIGNMENT-ACCESSION` supplies conditional ratification and integration authority only for this bounded inactive conformance programme. Every packet has `authority_delta: NONE_OUTSIDE_GRANTED_INACTIVE_CONFORMANCE_ENVELOPE`.

## 2. Repository baseline and exact inputs

- baseline: `origin/main` at `a24c11255cbaeeabc8fe12b99d4d975ef0a5922e`;
- predecessor: `RRSCG_CORE_COMPLETE_REPOSITORY_EFFECTIVE`, programme state v0.31;
- design: exact Revised 1 bytes and SHA-256 recorded in the ratification manifest;
- accession decision: `LSIAC-R2-GAP-06`, `ACCESSION_CANDIDATE`, `P2_AFTER_SINGLE_CLOCK_RRSCG_PARITY`;
- source census: WP0 census and exact Drive recovery ledger;
- transport: existing IROF `ovc.research_orchestration` types, authority registry and checkpoint machinery;
- owner read contract: existing C2 owner public structural snapshot boundary only;
- historical source: recovered exact Pine scripts are sealed historical/reference inputs, never executable source authority.

## 3. Packet sequence

### `MCAC-WP0` — court record, source census, reuse, design and plan ratification

Dependencies: RRSCG-CORE terminal state and current LSIAC accession decision.  
Deliverables: current-state preflight, source census, recovery ledger, reuse matrix, frozen design and reviews, ratification manifest, frozen implementation plan and plan review.  
Acceptance: exact hashes resolve; review is `PASS` or every required amendment is closed; no governing contradiction; all source gaps are typed by implementation relevance.

### `MCAC-WP1` — contracts, schemas, clock registry and negative doctrine

Dependencies: `MCAC-WP0`.  
Deliverables: immutable `ClockCoordinateIdentity`, mutable `ClockRegistryEntry`, occurrence/comparability/result contracts, JSON Schemas, clock registry, protected non-equivalence registry, machine-readable negative doctrine, canonical hashes.  
Acceptance: schema validation; alias rejection; owner-generation separation; doctrine binding and tamper rejection; no execution-authority effect.

### `MCAC-WP2` — causal alignment, containment and correspondence

Dependencies: `MCAC-WP1`.  
Deliverables: reference-first exact interval/point relation engine, comparability precedence, FVT decision, temporal-containment helper and deterministic correspondence engine.  
Acceptance: exhaustive mutually-exclusive edge goldens; FVT causality; gaps/censoring/generation rejection; all correspondence cardinalities; ambiguity/no-match/not-comparable/not-evaluable; morphology never becomes identity; reference/optimised equivalence.

### `MCAC-WP3` — RRSCG consumer and IROF transport

Dependencies: `MCAC-WP2`, RRSCG-CORE integrated, IROF present.  
Deliverables: owner-record-reference-only RRSCG comparison adapter, MCAC IROF `StageSpec`/profile, source-use class preflight and inactive authority registry.  
Acceptance: adapters cannot dereference private owner payload or reconstruct C2/C2E; full coordinate identity is retained; synthetic and sealed-consumed inputs pass; fresh owner-derived execution without exact owner authority fails; consumer receives no new authority.

### `MCAC-WP4` — historical/reference and adversarial conformance

Dependencies: `MCAC-WP3`.  
Deliverables: recovered historical source manifest, consumed-evidence parity receipt, negative/source-unavailable receipt, synthetic adversarial fixture pack and fixtures for historical doctrine.  
Acceptance: exact recovered bytes rehash; no journal reconstruction; exact historical computation reproduction is either exact and typed or `NOT_REPRODUCIBLE_EXACT_ARTIFACT_UNAVAILABLE`; the latter is non-blocking only when not implementation-defining; no fresh scientific confirmation claim.

### `MCAC-WP5` — replay, checkpoint, capacity and terminal accession

Dependencies: `MCAC-WP4`.  
Deliverables: chunk/full/order/checkpoint qualification, bound capacity profile, complete QA packet, packet gate decisions, terminal programme state and receipt, current-state pointer advancement.  
Acceptance: targeted and full repository assurance pass; VIT and GRT exact-tree pass; SIQ and PDC pass when required by current repository law; merge readiness; all packet gates delegated `PASS`; terminal authority exactly inactive and non-scientific.

Packets integrate in one bounded accession PR because the type contracts and consumers are one atomic inactive capability. Gate receipts still bind and close each packet separately. No packet may be marked complete before its prerequisite is satisfied.

## 4. Source bindings

Source use is exhaustive and typed:

- `SYNTHETIC`: MCAC adversarial fixtures; execution allowed inside this programme;
- `SEALED_CONSUMED_REFERENCE`: exact recovered Laboratory sources and repository-preserved receipts; hashing/parity only, never fresh market evidence;
- `OWNER_PUBLISHED_DERIVED`: public owner-authoritative records, permitted only with an exact current owner binding;
- `LOCATOR_ONLY`: evidentiary journal and source passports; discovery/lineage only, never algorithm reconstruction;
- `UNAVAILABLE_CONTEXT`: missing historical result/closeout artifacts that do not define MCAC implementation semantics;
- `FORBIDDEN`: private-owner reconstruction, raw/fresh real-source multiclock execution, `TV120_NATIVE`/`2H_A_L` aliasing and any ungranted source.

Every run binds source-use class, both complete coordinate identities, representation IDs, source generations, rule ID/version/hash, doctrine ID/hash, authority decisions and the maximum dependency FVT.

## 5. Implementation namespace and reuse

Implementation lives at `ovc.research_operations.mcac`. It may import `ovc.research_orchestration` stable serialization, models, authority and checkpoint functions. It adds no runner, scheduler, generic cache, evidence store or authority service. RRSCG integration is a read-only adapter in the MCAC namespace. Schemas and registries live under existing `schemas/research_operations` and `registries/research_operations` roots.

## 6. Test and QA matrix

Required targeted assurance includes:

- contract and JSON Schema validation;
- canonical serialization and content-address tamper rejection;
- all interval and point relations, inverse relations and boundary equality;
- FVT availability over every dependency and explicit retrospective-only results;
- source gaps, censoring, not-comparable and not-evaluable precedence;
- cross-generation rejection and explicit generation-bridge binding;
- protected clock alias rejection, including `TV120_NATIVE != 2H_A_L`;
- temporal containment is not compositional hierarchy;
- morphological resemblance is correspondence evidence, never identity;
- one-to-one, one-to-many, many-to-one, many-to-many, no-match and ambiguous correspondence;
- deterministic global correspondence finalisation;
- full/chunked, clean/restart and input-order equivalence;
- reference/optimised equivalence;
- missing-owner and private-payload rejection;
- doctrine-presence and downstream non-authority tests;
- source-manifest byte/hash integrity and historical-parity classification;
- capacity within the bound profile and fail-closed `CAPACITY_EXCEEDED` beyond each bound.

The current test population is collected at qualification time and recorded, never hardcoded. Full repository pytest and unittest suites run from the exact candidate tree. VIT, GRT, SIQ, PDC and merge-readiness use the repository-current canonical procedures discovered on the integration baseline.

## 7. Determinism, checkpoint and capacity qualification

The reference engine is normative. Any optimised path must produce byte-identical canonical results. Candidate edges are globally finalised by stable identities; chunks contain only associative accumulators; output is sorted canonically. Checkpoints bind plan/design/rule/doctrine/registry/input hashes and reject mismatch.

The capacity profile is `OVC.MCAC.CAPACITY.SYNTHETIC.v0.1`: at most 20,000 occurrences per side, 40,000 total, 2,000,000 candidate pairs, 512 MiB resident-memory growth, 60 seconds for the canonical 20,000-pair synthetic run, and input chunks no larger than 512 occurrences. A exceeded limit emits `CAPACITY_EXCEEDED`, incomplete telemetry and no complete scientific result.

## 8. Gate and state semantics

Machine state records for every packet: `packet_id`, `plan_id`, `plan_version`, `status`, `prerequisites`, `authority_required`, `authority_delta`, `baseline_commit`, `branch`, `candidate_commit`, `tests`, `qa_packet`, `decision_record`, `merge_commit`, `blockers`, `next_packet`.

Allowed progression is `PLANNED -> IMPLEMENTED -> QA_PASS -> DELEGATED_PASS -> REPOSITORY_EFFECTIVE`. A packet cannot skip prerequisites. Candidate commits remain provisional until exact-tree integration. The terminal state and receipt are prepared with `merge_commit: PENDING_PHYSICAL_MERGE`, then a merge receipt records the physical squash commit and advances the current-state pointer correct-forward on the next lawful main when repository convention requires a sealed-receipt follow-up.

## 9. Integration, build-ahead and rollback

- branch from exact current `origin/main`; never alter unrelated worktrees;
- commit and push without force;
- create one bounded PR with complete packet/gate evidence;
- if main changes, rebase or merge current main without rewriting published history, rerun base-sensitive tests, and record exact candidate/main/VIT/GRT trees;
- while checks run, construct only successor evidence that depends on frozen interfaces, labelled provisional until prerequisites land;
- squash-merge only after all required checks and merge-readiness pass;
- rollback is `git revert` of the squash merge plus correct-forward programme-state/pointer record; recovered source files remain immutable evidence and must not be destructively deleted;
- a failed check invalidates only dependent gate evidence; corrected evidence supersedes it with lineage.

## 10. Operator-reserved exclusions and stop conditions

Implementation must stop rather than invent authority if completion requires a new clock/source/provider/instrument/side, fresh real-source multiclock science, an unresolved implementation-defining source identity, new scientific semantics, active discovery/development/validation, selector/family/model/theory promotion, shared phase ontology, publication, probability, risk, exposure, trading or execution. Synthetic fixtures and exact consumed artifacts are the default substitute.

## 11. Terminal Definition of Done

The programme is terminal only when the reviewed design and plan are ratified with exact hashes; WP0-WP5 are repository-effective; clock identity, causal alignment, non-compositional nesting and non-identifying correspondence are implemented; negative doctrine is machine-readable and enforced; RRSCG and IROF adapters exist; lawful parity and source-unavailable classifications are recorded; replay/checkpoint/chunk/order/capacity assurance passes; all required repository checks pass; the PR is integrated; a terminal receipt exists; and the LSIAC current pointer advances.

Terminal authority is exactly: capability `INACTIVE`; scientific role `DESCRIPTIVE / RESEARCH OPERATIONS UTILITY`; new clock authority `NONE`; active Discovery authority `NONE_FROM_THIS_PROGRAMME`; Validation `LOCKED_UNCONSUMED`; publication `NONE`; probability/risk/exposure/trading/execution `NONE`.

No successor science begins automatically. The terminal report identifies the next lawful LSIAC route from the then-current court record.

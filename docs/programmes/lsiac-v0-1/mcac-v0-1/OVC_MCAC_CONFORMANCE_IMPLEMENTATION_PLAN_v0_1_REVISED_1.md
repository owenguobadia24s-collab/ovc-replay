# OVC MCAC Conformance Implementation Plan v0.1

Programme: `OVC-MCAC-v0.1`  
Capability: `OVC.MCAC.INACTIVE.DESCRIPTIVE.UTILITY.v0.1`  
Design input: `OVC_MCAC_DESIGN_SPECIFICATION_v0_1_REVISED_2.md`, SHA-256 `11b24d97dd24fe2d98d9179ca63f0688cb4d753d6049324685a760d87488eace`  
Status: `REVISED_1_REVIEW_CANDIDATE`

## 1. Purpose and authority envelope

This plan materialises the reviewed MCAC design as a small repository-native Research Operations capability. It implements deterministic, read-only, clock-explicit comparison machinery and preserves historical negative doctrine. It creates no clock, source, market, scientific selector, phase/state ontology, probability, validation, publication, risk, exposure, trading or execution authority. The capability remains `INACTIVE`; Validation remains `LOCKED_UNCONSUMED`.

The operator mandate `OVC RUN MULTICLOCK-COORDINATE-ALIGNMENT-ACCESSION` supplies conditional ratification and integration authority only for this bounded inactive conformance programme. Every packet has `authority_delta: NONE_OUTSIDE_GRANTED_INACTIVE_CONFORMANCE_ENVELOPE`.

## 2. Repository baseline and exact inputs

- baseline: `origin/main` at `a24c11255cbaeeabc8fe12b99d4d975ef0a5922e`;
- predecessor: `RRSCG_CORE_COMPLETE_REPOSITORY_EFFECTIVE`, programme state v0.31;
- design: exact Revised 2 bytes and SHA-256 `11b24d97dd24fe2d98d9179ca63f0688cb4d753d6049324685a760d87488eace` recorded in the ratification manifest, every checkpoint identity and terminal receipt;
- accession decision: `LSIAC-R2-GAP-06`, `ACCESSION_CANDIDATE`, `P2_AFTER_SINGLE_CLOCK_RRSCG_PARITY`;
- source census: WP0 census and exact Drive recovery ledger;
- transport: existing IROF `ovc.research_orchestration` types, authority registry and checkpoint machinery;
- owner read contract: existing C2 owner public structural snapshot boundary only;
- historical source: recovered exact Pine scripts are sealed historical/reference inputs, never executable source authority.

## 3. One integration packet and six workstreams

`MCAC-ACC-v0.1` is the programme's single atomic integration packet. `MCAC-WS0` through `MCAC-WS5` are dependent evidence workstreams inside that packet, not separately integrated packets. `MCAC-G0..G5` are internal conformance gates. They may reach delegated `PASS` before the one packet merges because they do not claim repository effectiveness; the packet alone becomes `REPOSITORY_EFFECTIVE` after physical integration. This avoids representing an unmerged workstream as a repository-effective predecessor.

### `MCAC-WS0` — court record, source census, reuse, design and plan ratification

Dependencies: RRSCG-CORE terminal state and current LSIAC accession decision.  
Deliverables: current-state preflight, source census, recovery ledger, reuse matrix, frozen design and reviews, ratification manifest, frozen implementation plan and plan review.  
Acceptance: exact hashes resolve; review is `PASS` or every required amendment is closed; no governing contradiction; all source gaps are typed by implementation relevance.

### `MCAC-WS1` — contracts, schemas, clock registry and negative doctrine

Dependencies: `MCAC-WS0` internal gate `MCAC-G0`.  
Deliverables: immutable `ClockCoordinateIdentity`, mutable `ClockRegistryEntry`, occurrence/comparability/result contracts, JSON Schemas, clock registry, protected non-equivalence registry, machine-readable negative doctrine, canonical hashes.  
Acceptance: schema validation; alias rejection; owner-generation separation; doctrine binding and tamper rejection; no execution-authority effect.

### `MCAC-WS2` — causal alignment, containment and correspondence

Dependencies: `MCAC-WS1` internal gate `MCAC-G1`.  
Deliverables: reference-first exact interval/point relation engine, comparability precedence, FVT decision, temporal-containment helper and deterministic correspondence engine.  
Acceptance: exhaustive mutually-exclusive edge goldens; FVT causality; gaps/censoring/generation rejection; all correspondence cardinalities; ambiguity/no-match/not-comparable/not-evaluable; morphology never becomes identity; reference/optimised equivalence.

### `MCAC-WS3` — RRSCG consumer and IROF transport

Dependencies: `MCAC-WS2` internal gate `MCAC-G2`, RRSCG-CORE integrated, IROF present.  
Deliverables: owner-record-reference-only RRSCG comparison adapter, MCAC IROF `StageSpec`/profile, source-use class preflight and inactive authority registry.  
Acceptance: adapters cannot dereference private owner payload or reconstruct C2/C2E; full coordinate identity is retained; synthetic and sealed-consumed inputs pass; fresh owner-derived execution without exact owner authority fails; consumer receives no new authority.

### `MCAC-WS4` — historical/reference and adversarial conformance

Dependencies: `MCAC-WS3` internal gate `MCAC-G3`.  
Deliverables: recovered historical source manifest, consumed-evidence parity receipt, negative/source-unavailable receipt, synthetic adversarial fixture pack and fixtures for historical doctrine.  
Acceptance: exact recovered bytes rehash; no journal reconstruction; exact historical computation reproduction is either exact and typed or `NOT_REPRODUCIBLE_EXACT_ARTIFACT_UNAVAILABLE`; the latter is non-blocking only when not implementation-defining; no fresh scientific confirmation claim.

### `MCAC-WS5` — replay, checkpoint, capacity and terminal accession

Dependencies: `MCAC-WS4` internal gate `MCAC-G4`.  
Deliverables: chunk/full/order/checkpoint qualification, bound capacity profile, complete QA packet, packet gate decisions, terminal programme state and receipt, current-state pointer advancement.  
Acceptance: targeted and full repository assurance pass; VIT and GRT exact-tree pass; SIQ and PDC pass when required by current repository law; merge readiness; all packet gates delegated `PASS`; terminal authority exactly inactive and non-scientific.

The workstreams materialise in one bounded accession PR because the type contracts and consumers are one atomic inactive capability. Internal gate receipts bind and close each workstream in dependency order. Only `MCAC-ACC-v0.1` has integration and repository-effective state.

## 4. Source bindings

Source use is exhaustive and uses the exact design vocabulary:

- `SYNTHETIC_CONFORMANCE`: MCAC adversarial fixtures; execution allowed inside this programme;
- `SEALED_CONSUMED_REFERENCE`: exact recovered Laboratory sources and repository-preserved receipts; hashing/parity only, never fresh market evidence;
- `OWNER_PUBLISHED_DERIVED_RECORDS`: public owner-authoritative records, permitted only with an exact current owner binding;
- `LOCATOR_ONLY`: evidentiary journal and source passports; discovery/lineage only, never algorithm reconstruction;
- `UNAVAILABLE_CONTEXT`: missing historical result/closeout artifacts that do not define MCAC implementation semantics;
- `FORBIDDEN`: private-owner reconstruction, raw/fresh real-source multiclock execution, `TV120_NATIVE`/`2H_A_L` aliasing and any ungranted source.

Every run binds source-use class, both complete coordinate identities, representation IDs, source generations, rule ID/version/hash, doctrine ID/hash, authority decisions and the maximum dependency FVT. `SEALED_CONSUMED_REFERENCE` passes only with a separately effective reference authority. Recovered Pine bytes receive exact lineage/hash verification only; historical computational parity requires an exact result artifact and cannot be inferred from source code or the journal.

## 5. Implementation namespace and reuse

Implementation lives at `ovc.research_operations.mcac`. It may import `ovc.research_orchestration` stable serialization, models, authority and checkpoint functions. It adds no runner, scheduler, generic cache, evidence store or authority service. RRSCG integration is a read-only adapter in the MCAC namespace. Schemas and registries live under existing `schemas/research_operations` and `registries/research_operations` roots.

## 6. Test and QA matrix

Required targeted assurance includes:

- contract and JSON Schema validation;
- canonical serialization and content-address tamper rejection;
- all interval and point relations, inverse relations and boundary equality;
- FVT availability over every dependency and explicit retrospective-only results;
- source gaps, censoring, not-comparable and not-evaluable precedence;
- exact ordered per-side generation-pair binding, plus mandatory rejection of within-side generation or segment stitching;
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

Machine state records the integration packet and every workstream. The packet record contains `packet_id`, `plan_id`, `plan_version`, `status`, `prerequisites`, `authority_required`, `authority_delta`, `baseline_commit`, `branch`, `candidate_commit`, `tests`, `qa_packet`, `decision_record`, `merge_commit`, `blockers`, `next_packet`. Each workstream records its ID, internal prerequisite gate, status, tests, QA packet, decision and blocker list.

The integration packet progresses `PLANNED -> IMPLEMENTED -> QA_PASS -> DELEGATED_PASS -> REPOSITORY_EFFECTIVE`. Workstreams progress `PLANNED -> PROVISIONAL_BUILD_AHEAD -> IMPLEMENTED -> QA_PASS -> DELEGATED_PASS`; they never claim repository effectiveness. A workstream cannot pass before its internal prerequisite gate, but provisional successor construction may proceed against the exact candidate SHA. Before each successor gate, it re-anchors to that exact same atomic candidate tree after the predecessor's internal gate and reruns all affected base-sensitive tests. The accession PR is eligible after all internal gates are delegated `PASS`; only its physical merge makes the composite packet and all its workstreams repository-effective. The terminal state and receipt are prepared with `merge_commit: PENDING_PHYSICAL_MERGE`, then a merge receipt records the physical squash commit and advances the current-state pointer correct-forward on the next lawful main when repository convention requires a sealed-receipt follow-up.

## 9. Integration, build-ahead and rollback

- branch from exact current `origin/main`; never alter unrelated worktrees;
- commit and push without force;
- create one bounded PR for the single integration packet with complete workstream/gate evidence;
- if main changes before publication, create a fresh correct-forward branch if needed; after publication, reconcile only through a non-rewriting merge or a separately created correct-forward branch/PR with preserved predecessor lineage; rebasing/rewriting published history and force-push are forbidden;
- while checks run, construct only successor evidence that depends on frozen interfaces, labelled provisional until prerequisites land;
- squash-merge only after all required checks and merge-readiness pass;
- rollback is `git revert` of the squash merge plus correct-forward programme-state/pointer record; recovered source files remain immutable evidence and must not be destructively deleted;
- a failed check invalidates only dependent gate evidence; corrected evidence supersedes it with lineage.

## 10. Operator-reserved exclusions and stop conditions

Implementation must stop rather than invent authority if completion requires a new clock/source/provider/instrument/side, fresh real-source multiclock science, an unresolved implementation-defining source identity, new scientific semantics, active discovery/development/validation, selector/family/model/theory promotion, shared phase ontology, publication, probability, risk, exposure, trading or execution. Synthetic fixtures and exact consumed artifacts are the default substitute.

## 11. Terminal Definition of Done

The programme is terminal only when the reviewed design and plan are ratified with exact hashes; MCAC-WS0 through MCAC-WS5 hold internal delegated `PASS`; the composite `MCAC-ACC-v0.1` packet is repository-effective; clock identity, causal alignment, non-compositional nesting and non-identifying correspondence are implemented; negative doctrine is machine-readable and enforced; RRSCG and IROF adapters exist; lawful parity and source-unavailable classifications are recorded; replay/checkpoint/chunk/order/capacity assurance passes; all required repository checks pass; the PR is integrated; a terminal receipt exists; and the LSIAC current pointer advances.

Terminal authority is exactly: capability `INACTIVE`; scientific role `DESCRIPTIVE / RESEARCH OPERATIONS UTILITY`; new clock authority `NONE`; active Discovery authority `NONE_FROM_THIS_PROGRAMME`; Validation `LOCKED_UNCONSUMED`; publication `NONE`; probability/risk/exposure/trading/execution `NONE`.

No successor science begins automatically. The terminal report identifies the next lawful LSIAC route from the then-current court record.

## 12. Frozen artifact, gate and command manifest

Output content hashes are late-bound at materialisation; the following identities and paths are frozen.

`MCAC-G0` closes WP0 from:

- `docs/design/research_operations/mcac-v0-1/OVC_MCAC_DESIGN_SPECIFICATION_v0_1.md`, `OVC_MCAC_DESIGN_REVIEW_v0_1.json`, `OVC_MCAC_DESIGN_SPECIFICATION_v0_1_REVISED_1.md`, `OVC_MCAC_DESIGN_REVISED_1_CLOSURE_REVIEW_v0_1.json`, ratified `OVC_MCAC_DESIGN_SPECIFICATION_v0_1_REVISED_2.md`, `OVC_MCAC_DESIGN_REVISED_2_CLOSURE_REVIEW_v0_1.json`, and `OVC_MCAC_DESIGN_RATIFICATION_v0_1.json`;
- this original plan, `OVC_MCAC_IMPLEMENTATION_PLAN_REVIEW_v0_1.json`, this Revised 1 plan, `OVC_MCAC_IMPLEMENTATION_PLAN_REVISED_1_CLOSURE_REVIEW_v0_1.json`, and `OVC_MCAC_IMPLEMENTATION_PLAN_RATIFICATION_v0_1.json`, all in the programme root;
- `docs/programmes/lsiac-v0-1/mcac-v0-1/wp0/MCAC_WP0_CURRENT_STATE_PREFLIGHT_v0_1.json`;
- `docs/programmes/lsiac-v0-1/mcac-v0-1/wp0/MCAC_WP0_SOURCE_CENSUS_v0_1.json`, SHA-256 `d7ca96ac7eb06f3ffb45944e41b240ddbf1655c95fff3a59880285ea27d97157` at plan freeze;
- `docs/programmes/lsiac-v0-1/mcac-v0-1/wp0/MCAC_WP0_REUSE_MATRIX_v0_1.json`;
- `docs/programmes/lsiac-v0-1/mcac-v0-1/wp0/MCAC_WP0_RATIFICATION_MANIFEST_v0_1.json`;
- `docs/programmes/lsiac-v0-1/mcac-v0-1/wp0/MCAC_G0_DECISION_v0_1.json`.

`MCAC-G1` closes WP1 from:

- `src/ovc/research_operations/mcac/contracts.py` and `src/ovc/research_operations/mcac/doctrine.py`;
- `schemas/research_operations/mcac/clock_coordinate_v0_1.schema.json`, `clock_indexed_occurrence_ref_v0_1.schema.json`, `comparison_result_v0_1.schema.json`;
- `registries/research_operations/mcac/MCAC_CLOCK_REGISTRY_v0_1.json`, `MCAC_PROTECTED_NON_EQUIVALENCE_v0_1.json`, `MCAC_NEGATIVE_DOCTRINE_v0_1.json`;
- `tests/research_operations/mcac/test_contracts_and_doctrine.py`;
- `docs/programmes/lsiac-v0-1/mcac-v0-1/wp1/MCAC_WP1_QA_v0_1.json` and `MCAC_G1_DECISION_v0_1.json`.

`MCAC-G2` closes WP2 from:

- `src/ovc/research_operations/mcac/alignment.py` and `correspondence.py`;
- `fixtures/research_operations/mcac/MCAC_INTERVAL_RELATION_GOLDENS_v0_1.json` and `MCAC_ADVERSARIAL_FIXTURES_v0_1.json`;
- `tests/research_operations/mcac/test_alignment.py` and `test_correspondence.py`;
- `docs/programmes/lsiac-v0-1/mcac-v0-1/wp2/MCAC_WP2_QA_v0_1.json` and `MCAC_G2_DECISION_v0_1.json`.

`MCAC-G3` closes WP3 from:

- `src/ovc/research_operations/mcac/rrscg_adapter.py` and `irof.py`;
- `registries/research_operations/mcac/MCAC_IROF_STAGE_PACK_v0_1.json` and `MCAC_SOURCE_USE_CLASS_REGISTRY_v0_1.json`;
- `tests/research_operations/mcac/test_rrscg_adapter.py` and `test_irof.py`;
- `docs/programmes/lsiac-v0-1/mcac-v0-1/wp3/MCAC_WP3_QA_v0_1.json` and `MCAC_G3_DECISION_v0_1.json`.

`MCAC-G4` closes WP4 from:

- `docs/programmes/lsiac-v0-1/mcac-v0-1/source-census/MCAC_RECOVERED_ARTIFACT_MANIFEST_v0_1.json` and immutable files below `source-census/recovered/google-drive/`;
- `docs/programmes/lsiac-v0-1/mcac-v0-1/wp4/MCAC_HISTORICAL_PARITY_RECEIPT_v0_1.json` and `MCAC_NEGATIVE_SOURCE_UNAVAILABLE_RECEIPT_v0_1.json`;
- `tests/research_operations/mcac/test_historical_reference.py`;
- `docs/programmes/lsiac-v0-1/mcac-v0-1/wp4/MCAC_WP4_QA_v0_1.json` and `MCAC_G4_DECISION_v0_1.json`.

`MCAC-G5` closes WP5 from:

- `src/ovc/research_operations/mcac/qualification.py`;
- `registries/research_operations/mcac/MCAC_CAPACITY_PROFILE_v0_1.json`;
- `tests/research_operations/mcac/test_replay_checkpoint_capacity.py`;
- `docs/programmes/lsiac-v0-1/mcac-v0-1/wp5/MCAC_WP5_QA_v0_1.json`, `MCAC_G5_DECISION_v0_1.json` and `MCAC_TERMINAL_RECEIPT_v0_1.json`;
- `records/research_operations/lsiac/LSIAC_PROGRAMME_STATE_v0_32.json` and repository-authoritative `records/research_operations/lsiac/CURRENT_STATE_POINTER.json`, verified as a correct-forward advance from v0.31 to v0.32.

The exact authority/source baseline binds:

- C2 owner read authority `AUTH.OPT-B.C2.vNext.OWNER_STRUCTURAL_SNAPSHOT.READ.v0.1`, owner generation `C2VNEXT.OWNER.GENERATION.ASR00.C2AR-PACKAGE-v1.READ-v0.1`, authority file SHA-256 `2269494d7871ce34fbe67a0fc826c1f7ad15d8872a94cbbb492726ef130113c4`, and current read-surface SHA-256 `e10d203b04a94ae11ce1ace9b98c5cf43ddfc80ae7963431c190f18451598deb`;
- RRSCG stage pack `RRSCG.IROF.STAGE.PACK.v0.1`, SHA-256 `47ced1bc84597544bc0e88891869aee5e15410144591389f4c70bf64d60a9bee`;
- IROF pointer `registries/implementation/irof/CURRENT_STATE_POINTER.json`, SHA-256 `891e87bc2dc57624cee8ee39e314e8d7b412fa6549c7364a1cdd191e4d22ae9a`, status `COMPLETED / INACTIVE_INFRASTRUCTURE_AVAILABLE`;
- each sealed recovered file by Drive ID/title/size/SHA-256 in `MCAC_RECOVERED_ARTIFACT_MANIFEST_v0_1.json`.

Targeted commands are `python -m pytest -q tests/research_operations/mcac` and `python -m unittest discover -s tests -p 'test*.py'` for applicable unittest population; schema checks run through targeted pytest. Full qualification uses repository-current canonical pytest/unittest, VIT, GRT, SIQ, PDC and merge-readiness commands discovered on the exact integration base, with the resolved commands, counts, durations and hashes recorded in WP5 QA rather than assumed here.

## 13. Revised 1 amendment closure

This revision binds ratified-design candidate Revised 2; freezes artifact/gate/QA/test identities and exact baseline source bindings; uses exact source-use vocabulary; forbids parity inference from recovered code; corrects generation language; defines one true atomic integration packet with six dependency-ordered internal workstreams and non-effective gates; and prohibits published-history rebasing. The frozen original plan remains preserved and is not ratified.

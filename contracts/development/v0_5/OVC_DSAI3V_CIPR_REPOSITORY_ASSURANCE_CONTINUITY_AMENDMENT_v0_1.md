# OVC DSAI3V + CIPR Repository Assurance Continuity Amendment v0.1

Status: OPERATOR RUN MANDATE / BOUNDED IMPLEMENTATION AND SHADOW QUALIFICATION AUTHORISED  
Programme ID: `OVC-DSAI3V-CIPR-REPOSITORY-ASSURANCE-CONTINUITY-AMENDMENT-0.1`  
Implementation namespace: `DSAI3V-RAC-WP*` / `DSAI3V-RAC-G*`  
Operator command: `OVC RUN OVC-DSAI3V-CIPR-REPOSITORY-ASSURANCE-CONTINUITY-AMENDMENT-0.1`  
Command date: 2026-08-24  
Execution baseline: `main@15c7531c3635e96681dc87b906455969fe21b6f3` / tree `2d799bf6454f50327c566c0c51fe7654d587ae85`  
Authority effect: development assurance and integration mechanics only; scientific/market authority `NONE`.

## 0. Primary decision

Complete the existing DSAI/VIT assurance-decoupling architecture by making repository assurance continuously addressable at claim and dependency level.

A new immutable packet MUST NOT pay the complete repository assurance cost merely because its branch or payload identity is new. The lawful blocking question becomes:

> Which previously certified assurance claims did this exact logical mutation invalidate?

The normal route is:

`certified RepositoryAssuranceGeneration + immutable PIP -> MutationImpactManifest -> DeltaAssurancePlan -> inherited valid proofs + delta assurance -> CandidateAssuranceCertificate -> VIT prospective tree -> current-main-sensitive exact-final assurance -> GRT -> SIQ -> physical main -> exact tree equality -> successor RepositoryAssuranceGeneration`.

The canonical complete repository suite remains the independent reference oracle and escalation path. It is not removed, weakened, relabelled or silently replaced by this amendment.

## 1. Constitutional ownership

### DSAI / VIT

DSAI/VIT owns assurance-reuse semantics, mutation-impact planning, PIP qualification, candidate certification, prospective composition and bounded recovery.

### CIPR

CIPR owns execution topology for an already-determined assurance obligation set. CIPR may optimise delta, wide and reference execution, but it MUST NOT decide that an assurance obligation is semantically unnecessary.

### GRT

GRT remains the sole owner of Repository Constitution law, GRT impact closure, exact integration-tree conformance and DebtFloor semantics.

### Shared Systems

Shared Systems may supply generic identity, dependency-impact, assurance, currentness, evidence and reference/optimised-equivalence primitives only under an exact current binding. Shared Systems does not acquire DSAI, CIPR or GRT semantics.

### SIQ and physical main

SIQ remains the existing serialized physical integration gateway. Physical `main` remains the sole operational court record. Parallel physical merge remains prohibited.

### System Atlas

System Atlas may later project assurance state read-only. Atlas is never an assurance source, repository-law owner or integration authority.

## 2. Assurance constitution

The existing A0-A3 constitution is preserved and refined:

- `A0A_INHERITED_REPOSITORY_ASSURANCE`: previously passed claim evidence whose declared dependencies remain unchanged.
- `A0B_PIP_LOCAL_ASSURANCE`: assurance over the immutable logical payload and its exact authority/dependency frontier.
- `A0C_DELTA_IMPACT_ASSURANCE`: newly executed claims selected by the deterministic impact closure.
- `A1_COMPOSITION_ASSURANCE`: deterministic application and prospective-tree composition.
- `A2_EXACT_FINAL_ASSURANCE`: current VIT generation, current authority/currentness, GRT and SIQ/PDC exact-final assurance.
- `A3_POST_WRITE_EQUIVALENCE`: physical tree equality and durable causal receipts.

`A0A + A0B + A0C` may satisfy the base-independent assurance requirement only when every reused claim is content-addressed, current, dependency-complete and admitted by this amendment. Missing dependency knowledge never becomes reuse authority.

## 3. Canonical objects

### AssuranceClaimSpec

Defines one independently reusable assurance claim with:

- exact `claim_id` and claim-spec identity;
- claim class;
- declared dependency tokens;
- harness generation;
- execution profile;
- wide-rerun, unbounded and reference-only flags.

The reusable unit is the assurance claim, not a whole PR run or a persuasive green workflow summary.

### AssuranceDependencyGraph

Deterministic derived graph from assurance claims to exact dependency tokens. It is rebuildable from normative claim records. It does not create repository ownership or scientific meaning.

### RepositoryAssuranceGeneration

Immutable certification for one exact physical Git tree, one claim graph, one policy generation and one harness generation. Claim states remain separate: passed, not evaluable and quarantined.

### MutationImpactManifest

PIP-bound manifest of changed paths, owners, contracts, schemas, authority records, harnesses, environments and other registered logical dependency tokens. Path lists alone are insufficient where multiple files share one semantic owner.

### DeltaAssurancePlan

Deterministic classification of every registered claim into exactly one state:

- `INHERIT_VALID`;
- `RERUN_REQUIRED`;
- `WIDE_RERUN_REQUIRED`;
- `FULL_REFERENCE_REQUIRED`;
- `NOT_EVALUABLE`;
- `QUARANTINED`.

Unknown or unclassified mutation surfaces fail closed to wider or full-reference execution.

### CandidateAssuranceCertificate

Content-addressed evidence that all required inherited, delta or reference obligations passed for the immutable PIP. It grants no programme, scientific or physical-main authority by itself.

### ReferenceReconciliationReceipt

Compares delta-path conclusions with the canonical reference execution. Unexplained disagreement is `ASSURANCE_MODEL_DIVERGENCE` and triggers quarantine and safe fallback.

## 4. Impact and invalidation rules

1. Dependency intersection is evaluated over exact declared logical tokens, not branch age, PR number, queue position or lexical path proximity.
2. Unrelated main movement is `PLACEMENT_ONLY` and MUST NOT create a new PIP, development commit, branch or PR.
3. A changed dependency invalidates only the transitive claim closure that declares or inherits that dependency.
4. Harness, runtime, requirements, authority-resolver, VIT-core, GRT-interface and other registered global changes may lawfully escalate to full reference.
5. `UNKNOWN`, missing graph coverage, malformed identities, ambiguous owner resolution or stale policy fail closed.
6. Runtime observation may add dependency edges. It may not autonomously remove an owner-declared or historically required dependency edge.
7. Removing or narrowing a claim requires a governed successor coverage record; deletion does not manufacture a PASS.
8. Cache loss causes deterministic rebuild or full-reference fallback, never assumed validity.

## 5. CIPR execution products

CIPR SHALL expose three execution roles:

- `DELTA_EXECUTOR`: exact selected claim set.
- `WIDE_EXECUTOR`: deterministic selected shard union for a large but bounded closure.
- `REFERENCE_EXECUTOR`: canonical complete repository assurance.

The qualified post-PYT pytest shard union is preserved as candidate evidence for `REFERENCE_EXECUTOR`. This amendment does not consume `CIPR-G5-POST-PYT-CONSOLIDATED-CUTOVER`, mutate required checks, retire visible contexts or activate required-check substitution.

## 6. Reference safety model

The incremental route is never self-authenticating.

Before pilot activation, every eligible shadow candidate MUST be dual-run against the complete reference route. After bounded activation, reference execution continues under a measured reconciliation schedule and is mandatory after incidents or material assurance-model changes.

If incremental PASS and reference FAIL disagree:

1. halt affected automatic admission;
2. quarantine the affected certificate and repository-assurance generations;
3. fall back to full reference for affected packet classes;
4. identify and append the missing/incorrect dependency edge;
5. correct forward;
6. independently requalify before reactivation.

## 7. Persistence and Git-churn boundary

Git stores contracts, schemas, policies, claim registries, qualification decisions and compact milestone receipts.

Routine RepositoryAssuranceGenerations, execution manifests and reconciliation receipts SHOULD use the governed durable evidence store. Reverse indexes, dependency caches and test-selection indexes remain rebuildable runtime state. Routine assurance evolution MUST NOT create a second ordinary post-merge PR.

## 8. Required adversarial assurance

Qualification MUST cover at least:

- same path with changed semantics;
- different paths sharing one logical owner;
- hidden contract consumer;
- changed authority/currentness record;
- changed harness, requirements or runtime;
- new unregistered production module;
- removed claim/test without successor coverage;
- unrelated main movement with empty dependency intersection;
- deep transitive dependency intersection;
- false unaffected classification;
- cache/index corruption and loss;
- reference/delta disagreement;
- three parallel PIPs with disjoint and overlapping closures;
- GRT-wide invalidation with narrow programme tests;
- physical-main movement during the integration lease.

Zero false proof reuse, zero missed affected claim, zero authority false allow, zero GRT mismatch and zero post-write tree mismatch are blocking.

## 9. Gate sequence

- `DSAI3V-RAC-G0`: SATISFIED by the exact operator RUN command. Authorises bounded design materialisation, implementation, synthetic/adversarial execution, historical replay and non-authoritative shadow qualification.
- `DSAI3V-RAC-G1-MECHANICAL`: AUTO_RATIFIABLE after object, schema, policy, reference-engine and deterministic-identity tests pass.
- `DSAI3V-RAC-G2-REFERENCE-EQUIVALENCE`: AUTO_RATIFIABLE after reference/delta truth-world equivalence and fail-closed adversarial tests pass.
- `DSAI3V-RAC-G3-SHADOW-QUALIFICATION`: AUTO_RATIFIABLE after measured multi-lane shadow evidence is complete with no unexplained divergence.
- `DSAI3V-RAC-G-DELTA-ASSURANCE-PILOT`: OPERATOR_REQUIRED before delta assurance may substitute for the canonical blocking suite for any live packet class.
- `DSAI3V-RAC-G-DELTA-ASSURANCE-GENERAL`: OPERATOR_REQUIRED before normal eligible permanent packets may use the mechanism generally.

## 10. Explicit non-grants

This amendment grants no new programme authority, scientific or market semantics, model/selector/family/candidate/theory promotion, active Discovery/Development/Validation transition, publication, probability, risk, exposure, trading, execution, parallel physical merge, force-push, history rewrite, destructive cleanup, ruleset mutation, required-check substitution or new physical-main writer.

Operator-required packets remain parked at their programme-owned boundaries.

## 11. Rollback

Rollback is forward-only. Disable delta reuse and return affected packet classes to fresh canonical reference assurance while preserving VIT/SIQ/GRT routing, all claims, graphs, generations, certificates, reconciliation receipts, operator decisions and Git history. A rollback MUST NOT reinterpret an earlier incremental PASS as scientific or repository authority.
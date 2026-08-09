# IROF-G0 — Design + Implementation Plan Ratification

**Programme:** OVC-IROF-v0.1  
**Gate:** IROF-G0  
**Gate type:** OPERATOR REQUIRED  
**Allowed decisions:** PASS / DEFER / BLOCK / QUARANTINE / SUPERSEDE  
**Recommended decision:** **PASS**  
**Status:** GATE_READY — STOP HERE UNTIL OPERATOR DECISION

---

## 1. Exact court-record baseline

- Repository: `owenguobadia24s-collab/ovc-replay`
- Lawful main at preflight: `ffefd1ee3d7ee664f2a94f74d05993d6e711a149`
- Main tree: `1176e5a9342561bf3a9e6d1ba21b09615e226108`
- Main decision: `SRFDI-G-JUNE-AUTH v0.6: fresh post-SFC delegated authorization`
- IROF branch: `design/irof-v0-1-g0`
- Candidate design/plan commit: `b263a50d5030347d332894788cc8dcb20e7996c5`
- Candidate design/plan tree: `25806c5652bd679c339b9582ce94b6b1018e211d`

The administrative child commit containing this decision packet/programme state is not a different technical candidate; `b263a50...` is the exact design/plan candidate under review.

---

## 2. Completed pre-G0 work

1. Inspected latest lawful main and relevant implementation/state.
2. Reconciled active/inactive authority for C2, C2E, SFC, SRFD, OccurrenceContext and Validation.
3. Inspected existing orchestration, replay, checkpoint, cache, capacity and evidence primitives.
4. Inspected historical full-stack synthetic rehearsal PR #418 as noncanonical source evidence.
5. Classified current open material PRs relevant to IROF.
6. Materialised:
   - `docs/design/irof-v0-1/OVC_INTEGRATED_RESEARCH_ORCHESTRATION_FRAMEWORK_DESIGN_SPECIFICATION_v0_1.md`
   - `docs/plans/irof-v0-1/OVC_INTEGRATED_RESEARCH_ORCHESTRATION_FRAMEWORK_IMPLEMENTATION_PLAN_v0_1.md`
7. No implementation code has been created or changed.

---

## 3. Current authority and relevant programme state

### C2

Active v2 Discovery selector exists. Development is remote-verified reference-only. Validation remains `LOCKED_UNCONSUMED`. No family/semantic/probability/risk/exposure/execution authority follows from C2.

### C2E v0.2

Current programme state remains deferred at its operator boundary. Real-source replay and WP6 are denied; active C2E and active boundary pack are NONE. PR #479 records two unresolved pre-run requirements for a June PASS supersession: a separately governed June-eligible empirical boundary pack and an exact C2E resource envelope.

### SFC / SRI / FDI

SFC is completed with disposition PRESERVED. The conformance chain and deterministic replay/capacity machinery are reusable implementation evidence; no canonical family method/catalog was created by SFC.

### SRFD

Current main records one exact bounded June SRFD authorization token as unconsumed. This is SRFD-owned authority only. IROF-G0 does not request it, consume it or combine it with other programme permissions.

### OccurrenceContext

v0.1 is completed as a frozen deterministic nonstructural upstream context contract. Current consumer code rejects `REPRESENTATION_INPUT`; IROF must preserve that default firewall.

### Research Operations

Existing canonical identity, artifact catalogue, non-mutating QA, storage/path governance and deterministic read-model machinery are implementation dependencies to reuse.

### Validation / E-H

Validation remains locked/unconsumed. Probability, risk, exposure, trading and execution authority remain NONE.

---

## 4. Architecture decision

Approve IROF as **cross-cutting infrastructure**, not another Option.

```text
PopulationSpec + PipelineProfile + versioned packs/config + AuthorityBindings
        -> IntegratedRunManifest
        -> typed stage DAG
        -> deterministic execution/reuse/restart
        -> StageExecutionReceipts + artifacts + QA
        -> IntegratedRunReceipt + Research Operations evidence
```

The orchestrator owns execution mechanics and authority enforcement. Scientific stages retain ownership of market semantics.

### Key architectural corrections from repository evidence

1. **DAG, not a linear hard-coded script.** SRFD already contains topological/resource-planning primitives; future MCARB/C2P/C2.5/C3/OPT-C/OPT-D require branches and optional dependencies.
2. **OccurrenceContext is an orthogonal context branch.** It is not silently inserted into structural representation.
3. **One architecture for synthetic and real populations.** Differences live in PopulationSpec provenance/source adapter/authority binding, not downstream scheduler semantics.
4. **Conform-and-generalise.** Generic SRFD/SFC/C2E primitives are extracted or wrapped only with exact compatibility proof.
5. **Per-node authority.** IROF cannot compose partial external grants into a whole-pipeline grant.

---

## 5. Exact reuse/refactor plan

| Existing source | Treatment |
|---|---|
| `src/ovc/opt_b/srfd/orchestration.py` | GENERALISE_WITH_EQUIVALENCE: generic deterministic stage/checkpoint/hash patterns; retain SRFD fixture compatibility |
| `src/ovc/opt_b/srfd/scheduler.py` | GENERALISE_WITH_EQUIVALENCE: generic topology/resource planning; SRFD family-method completeness remains SRFD-owned |
| `src/ovc/opt_b/srfd/semantic_cache.py` | GENERALISE_WITH_EQUIVALENCE: semantic key/quarantine/tile completion primitives |
| SRFD capacity modules | REUSE/GENERALISE observability and no-scope-change doctrine; scientific estimators remain stage-owned |
| `src/ovc/opt_b/sfc/replay.py` | ADAPTER/INVARIANT source for replay manifests, checkpoint/resume, capacity and interlock behavior |
| `src/ovc/opt_b/c2e_v2/` | ADAPTER_ONLY; no episode repair/reconstruction |
| `src/ovc/context/occurrence_context/` | DIRECT_TYPED_ADAPTER; preserve nonstructural role and consumer firewall |
| `src/ovc/research_operations/` | DIRECT_SERVICE_REUSE for canonical identity, catalogue, QA, storage/read model |
| PR #418 FSR | HISTORICAL_FIXTURE_ONLY; port scenarios, do not merge/promote bespoke code |
| MCARB | REGISTER_AS_AUTHORITY_GATED_BRANCH; no automatic representation-input role |

---

## 6. New contracts proposed

The design freezes the need for these IROF-owned types; schemas are implemented in IROF-WP1 after PASS:

- PopulationSpec
- PipelineProfile
- StageSpec
- StageInvocation
- StageDependency
- AuthorityBinding
- ResearchRunSpec
- IntegratedRunManifest
- StageExecutionReceipt
- IntegratedRunReceipt
- ArtifactRef
- SemanticCacheKey
- CheckpointRecord
- RestartLedger
- CapacityBudget
- CapacityReceipt
- RunFailure
- RunComparisonRecord

The contracts separate semantic run identity, physical execution attempt identity and artifact location.

---

## 7. Proposed repository areas

No code area is changed before G0. After PASS, the bounded implementation may create/modify only packet-required paths, initially:

```text
src/ovc/research_orchestration/
contracts/research_orchestration/
schemas/research_orchestration/
registries/research_orchestration/
registries/implementation/irof/
fixtures/research_orchestration/
tests/research_orchestration/
docs/releases/irof-v0-1/
```

Minimal compatibility changes may touch existing SRFD/SFC/C2E/Research Operations test or adapter extension points only when a packet explicitly records them and scientific equivalence is proved.

---

## 8. Work-packet sequence

| Packet | Purpose | Gate |
|---|---|---|
| IROF-WP0 | latest-main preflight and conformance inventory | IROF-G1 AUTO |
| IROF-WP1 | core objects/schemas/registries/population/profile/run identity | IROF-G2 AUTO |
| IROF-WP2 | StageSpec adapter protocol, DAG and dependency planner | IROF-G3 AUTO |
| IROF-WP3 | authority resolver and population binding/dry-run | IROF-G4 AUTO |
| IROF-WP4 | semantic artifact cache/reuse | IROF-G5 AUTO |
| IROF-WP5 | checkpoint/restart/failure recovery | IROF-G6 AUTO |
| IROF-WP6 | capacity scheduler and computational telemetry | IROF-G7 AUTO |
| IROF-WP7 | Research Operations/QA/catalogue integration | IROF-G8 AUTO |
| IROF-WP8 | current-layer adapters and canonical profiles | IROF-G9 AUTO |
| IROF-WP9 | current-boundary synthetic E2E golden integration | IROF-G10 AUTO |
| IROF-WP10 | deterministic multi-N performance characterization | IROF-G11 AUTO |
| IROF-WP11 | real-population preflight, extension proof, closeout | IROF-G12 AUTO closeout only |

Any separately reserved authority encountered is routed to the existing owning programme/gate, not converted into an IROF operator gate.

---

## 9. Test and QA strategy

Required programme-level proof includes:

- deterministic schema/serialization and run identity;
- topology/cycle/dependency checks;
- wrapper leakage rejection;
- denial-before-protected-read authority checks;
- semantic cache exactness, stale-key misses and corruption quarantine;
- fresh/repeat/restart equivalence;
- worker/scheduling-order logical equivalence;
- no-scope-change CAPACITY_EXCEEDED path;
- per-stage/whole-run telemetry with explicit unavailable metrics;
- Research Operations QA non-mutation and catalogue verification;
- frozen SRFD scientific behavior equivalence after any extraction;
- current-chain synthetic end-to-end run;
- multi-N scaling evidence;
- real-run dry-run authority failure;
- extension-stage registration without scheduler semantic changes.

No production SLA is proposed before WP10 measurement.

---

## 10. Capacity strategy

IROF generalises the already accepted SRFD principle: the scheduler may control resources but may not change the experiment.

Permitted: concurrency control, topological sequencing, verified reuse, stage-declared partitioning, checkpoint/restart, capacity stop.

Prohibited: population sampling, method dropping, sensitivity reduction, threshold change, denominator change, silent profile reduction or partial-as-complete reporting.

PR #433 is retained as a regression case demonstrating why capacity failure must remain distinct from scientific disposition.

---

## 11. Real-population boundary

IROF v0.1 implements real-population **preflight**, not a new real-run authority.

At current court record, a full-descriptive June request must return an authority-denied evidence packet because C2E real replay is blocked/deferred. The packet may expose reusable authorised ancestors and the separately owned SRFD token state, but MUST NOT consume the SRFD token or substitute synthetic evidence.

A future real run through IROF is lawful only when every requested node's owning authority explicitly permits that invocation.

---

## 12. Risks / warnings

### W1 — Current C2E real-run blocker

Not an IROF design blocker; it is mandatory authority-firewall evidence. A real full-descriptive run remains unavailable.

### W2 — SRFD current token

A live exact bounded SRFD token exists. IROF implementation must ensure dry-run/preflight cannot consume or broaden it.

### W3 — SRFD refactor drift

Generic extraction could change frozen v0.4 scientific behavior. Mitigation: compatibility wrapper first, exact logical-equivalence tests, rollback to original implementation on any drift.

### W4 — telemetry portability

CPU/RSS/IO metrics differ by environment. Metrics are typed as measured/unavailable rather than fabricated zeroes; environment identity remains attempt-level, not semantic run identity.

### W5 — historical FSR temptation

PR #418 demonstrated integration but is not current canon. It may supply scenarios only.

No unresolved warning blocks design/plan ratification.

---

## 13. Rollback

Before implementation: close this PR and leave main unchanged.

After PASS: IROF remains additive. Packet rollback removes/unregisters the IROF layer and retains source-stage behavior/evidence. Any generic refactor touching SRFD is merged only with equivalence proof; otherwise IROF stays on adapters and the existing SRFD implementation remains intact. No historical decision is rewritten.

---

## 14. Exact authority requested at IROF-G0

### PASS would authorise

- repository programme state/packet evidence;
- contracts/schemas/registries;
- deterministic IROF code;
- synthetic fixture and generated-population execution;
- DAG planning/scheduling;
- read-only authority resolution and real-run preflight;
- semantic cache/reuse;
- checkpoint/restart;
- capacity/resource management;
- computational telemetry;
- Research Operations/QA/artifact/read-model integration;
- read-only adapters to current stage APIs;
- current-boundary local synthetic E2E runs;
- multi-N synthetic characterization;
- extension fixture;
- auto-ratification, commit/push and eligible squash merge of non-reserved packets under the approved plan.

### PASS would NOT authorise

- provider intake;
- real C2E June replay;
- consumption of the current SRFD June token;
- selector activation/replacement;
- ACTIVE_DISCOVERY/DEVELOPMENT/VALIDATION changes;
- Validation consumption;
- representation/normalization/distance/family promotion;
- active family catalogue;
- C2E activation or boundary-pack promotion;
- C2P semantic/identity authority;
- revised C2.5/C3 activation;
- canonical/R2 publication;
- probability/risk/exposure/trading/execution;
- agent write authority.

---

## 15. Acceptance conditions for IROF-G0 PASS

1. Design and plan are materially complete and consistent with repository court record.
2. IROF is cross-cutting and authority-neutral.
3. Existing scientific primitives are reused/conformed rather than duplicated.
4. OccurrenceContext remains nonstructural by default.
5. Synthetic/real share one orchestration architecture.
6. Current real authority asymmetry fails closed.
7. Cache/checkpoint/capacity semantics cannot mutate science.
8. Research Operations evidence is integrated rather than duplicated.
9. Packet/gate sequence contains no unnecessary operator gates.
10. Rollback is additive/non-destructive.
11. No code was implemented before G0.

**QA recommendation:** PASS.

---

## 16. Exact work after PASS

Upon `OVC APPROVE IROF-G0 PASS`:

1. record the operator decision in an append-only IROF decision record;
2. merge the G0 design/plan/decision packet to main through an eligible squash merge after exact-head assurance;
3. re-resolve latest lawful main;
4. start IROF-WP0 on a fresh bounded branch;
5. execute continuously through auto-ratifiable engineering gates;
6. stop only at a true reserved authority boundary, uncorrectable blocker or programme terminal boundary.

Until that command is received, **no IROF implementation code may begin**.

# PD Market-Description Reliability Review Contract v0.1

## Purpose

Define the minimum evidence and scoring rules required to determine whether a Pattern Discovery candidate description is factually correct, internally coherent, understandable and repeatable. This is a research-assurance contract only and grants no promotion, activation, publication or execution authority.

## Unit of review

One review unit is one immutable candidate window bound to:

- candidate-window identity and exact start/end timestamps;
- source slice, source binding, OPT-A/C1/C2 release and selector identities;
- first-valid trigger timestamp and frozen trigger snapshot;
- exact C1 facts and C2 states visible at the trigger cutoff;
- post-trigger candidate-window fingerprint;
- assigned cluster version, medoid and deterministic distance decomposition;
- exact price-path evidence for the declared review window;
- immutable evidence references and logical hashes.

## Required panel sections

1. **What the system says** — a finite list of factual, non-semantic claims.
2. **Why it says it** — each claim mapped to exact C1/C2/trigger evidence.
3. **What price did** — exact pre-trigger and post-trigger path, with no post-cutoff leakage into trigger claims.
4. **Structural comparison** — candidate fingerprint, assigned medoid, component distances, outlier threshold and overlap status.
5. **Contradictions and omissions** — evidence that weakens or conflicts with the system description.
6. **Uncertainty** — explicit `SUPPORTED`, `PARTIAL`, `CONTRADICTED`, `NOT_EVALUATED` or `NOT_APPLICABLE` state.

## Claim-level record

Every factual claim must contain:

- `claim_id`;
- `claim_text`;
- `claim_scope` from `PRE_TRIGGER`, `TRIGGER_TIME`, `POST_TRIGGER_WINDOW`, `STRUCTURAL_COMPARISON`;
- exact evidence references;
- chronology status;
- factual status;
- omission status;
- operator rationale;
- reproducibility status.

Free text without exact evidence references cannot support a reliability PASS.

## Review dimensions

### 1. Chronology integrity

- `PASS`: no claim uses information after its declared cutoff and trigger/candidate-window roles are explicit.
- `FAIL`: timestamps conflict, post-trigger information is presented as trigger evidence, or trigger persistence and candidate-window duration are conflated.

### 2. Factual correctness

- `SUPPORTED`: the exact source evidence directly supports the claim.
- `PARTIAL`: some but not all material parts are supported.
- `CONTRADICTED`: exact evidence conflicts with the claim.
- `NOT_EVALUATED`: required source evidence is unavailable.

### 3. Completeness

A description must expose material opposing or weakening facts. A technically true but materially incomplete description cannot receive a full reliability PASS.

### 4. Internal structural consistency

Candidate identity, trigger reason, fingerprint, medoid assignment, component distance, total distance, outlier classification, overlap state and frozen rule versions must reconcile exactly.

### 5. Review repeatability

The same immutable review unit and rubric must produce the same claim statuses in a delayed repeat review, subject only to an explicitly recorded operator disagreement.

## Population-level reliability

Population reliability cannot be inferred from only queue-promoted objects. A valid review set must include:

- every promoted pilot object;
- deterministic negative controls;
- a stratified sample of queue-suppressed candidates across clocks, trigger families, quality states, clusters and distance bands;
- explicit missingness and gapped-source strata.

## Minimum acceptance evidence

A statement that the system **consistently and reliably describes the market** requires all of the following:

- exact claim-level records for the review sample;
- no unresolved chronology failures;
- no concealed contradictory material facts;
- predefined sample construction and minimum size;
- repeat-review agreement evidence;
- separate reporting of promoted, suppressed and negative-control performance;
- no use of semantic or outcome promotion as a substitute for descriptive accuracy.

## Fail-closed rules

- Missing exact price windows => external validity `NOT_EVALUATED`.
- Missing console/candidate-detail bundle => panel usability and claim completeness `NOT_EVALUATED`.
- Deterministic rerun PASS alone => no external validity conclusion.
- `WORKFLOW_ACCEPTED` => workflow evidence only, never candidate or market-description approval.
- Gapped source => reliability conclusion restricted to observed complete windows and explicitly qualified.

## Prohibitions

This contract does not change formulas, trigger rules, candidate rules, clustering, distances, thresholds, selectors, releases, R2 objects or Validation locks. It does not create probability, risk, exposure, trading, execution or agent authority.

# PD-JUNE-FULL-MONTH-MDR Implementation Plan v0.1

## Court identity

- Plan ID: `OVC-PD-JUNE-FULL-MONTH-MDR.v0.1`
- Programme ID: `PD-JUNE-FULL-MONTH-MDR`
- Operator authority recorded: `2026-07-31T14:14:00Z`
- Baseline main: `6b34ffcc8d1b7168584432a650cde81c09ca9068`
- Superseded reliability question: the completed three-day CORR2 packet remains immutable historical evidence and is not rewritten.

## Purpose

Assess whether OVC C2 and Pattern Discovery descriptions are consistently reviewable across the whole of June 2026, rather than only the prior June 22–25 pilot slice. The assessment must reduce source-boundary-driven insufficient evidence by supplying deterministic late-May warm-up and early-July completion context.

This plan does not authorise canonical 2021–2023 Discovery processing.

## Target and source boundary

The scored target interval is exactly:

- start inclusive: `2026-06-01T00:00:00Z`
- end exclusive: `2026-07-01T00:00:00Z`

Only target timestamps may become June candidates, controls or scored review observations.

The source context interval is derived from the maximum frozen evidence horizon:

| Requirement | Frozen source | Horizon |
|---|---|---:|
| C2 15M level history | `levels.py`: 32 × 15M | 8 hours |
| C2 2H_A_L level history | `levels.py`: 24 × 2H | 48 hours |
| previous-state continuity | largest evaluated clock | 2 hours |
| repeated-switching trigger history | `evaluation.py`: 6 × 15M | 90 minutes |
| candidate completion horizon | this bounded study | 48 hours |

The maximum is 48 hours. Therefore the exact read-only source interval is:

- source start inclusive: `2026-05-30T00:00:00Z`
- source end exclusive: `2026-07-03T00:00:00Z`

May 30–31 and July 1–2 are context-only. They must never be counted as June target candidates or controls.

## Approved authority

The operator authorises:

- read-only Dukascopy GBPUSD BID/ASK intake for the exact source interval;
- deterministic M1, H1, 15M and 2H_A_L reconstruction needed by the existing approved pipeline;
- deterministic C1 and C2 replay without changing any formula, threshold, parameter pack, selector or release;
- whole-June target filtering;
- read-only trigger, candidate, control and review construction;
- evidence-completeness audits, blinded review cards, QA and gate packets;
- local external-artifact writes and compact repository receipts;
- bounded tests, CI, PR preparation and eligible squash merges.

## Retained prohibitions

No formula, semantic, trigger, candidate, distance, clustering, threshold or model change. No semantic, family, candidate, novelty or theory promotion. No selector or release mutation. No canonical 2021–2023 Discovery processing or append. No R2 publication. No Validation consumption. No probability, risk, exposure, trading, execution or agent-write authority.

## Work packets

### PD-JUNE-FM-00 — plan, authority and source-boundary freeze

Materialise this plan, operator authority record, source/review contract, deterministic source-profile implementation, tests, QA and machine-readable programme state.

Acceptance:

1. the target interval is exactly the whole of June 2026;
2. the context window is deterministically derived and equals May 30 through July 3, end exclusive;
3. May and July are context-only;
4. provider execution remains prohibited in CI;
5. no retained prohibition is weakened;
6. focused and complete repository tests pass.

This packet is auto-ratifiable because the operator has already approved the bounded authority in the instruction that created this plan.

### PD-JUNE-FM-WP1 — operator-local source intake and source QA

Perform immutable operator-local provider intake for:

- M1 BID and ASK daily partitions across the exact source interval;
- native H1 BID and ASK monthly transports for May, June and July 2026;
- exact clipping to the source interval;
- gap, duplicate, boundary, BID/ASK and native-H1 reconciliation QA;
- source inventory, hashes, manifests and freeze receipt.

Weekend market closures may be recorded as expected discontinuities. Unrecorded intra-session gaps, side mismatch, duplicate or non-monotonic rows, boundary truncation or OHLC reconciliation failures must block or quarantine.

### PD-JUNE-FM-WP2 — deterministic C1/C2 replay and whole-June population

Rebuild existing approved C1 and C2 outputs over the source interval. Filter target eligibility to June timestamps only. Preserve May and July records only as warm-up or completion context.

Acceptance includes:

- exact source binding;
- no `WINDOW_NOT_COMPLETE` caused solely by the June calendar boundary;
- complete previous-state and 2H-parent context wherever source data permits;
- unchanged C1/C2 formulas, parameter packs, selectors and identities;
- deterministic rerun equivalence.

### PD-JUNE-FM-WP3 — completeness audit and blinded review construction

Construct a whole-June review population and controls distributed across:

- all June weeks;
- BID and ASK;
- local and 2H-parent scopes;
- different UTC sessions;
- trigger and non-trigger observations;
- quality and persistence states.

Every review card must expose:

- complete pre-trigger and post-trigger state sequence;
- actual active-level values and relation identities;
- persistence history leading to the trigger;
- 15M OHLC and five C2 axes;
- corresponding 2H parent state where applicable;
- trigger timestamp and deterministic calculation;
- explicit source-completeness classification;
- separate trigger, structural, evidence-completeness and disposition questions.

A pre-review QA gate must report and distinguish:

- source-boundary insufficiency;
- provider-gap insufficiency;
- algorithmic `NOT_EVALUATED` or `NOT_EVALUABLE` states;
- card-presentation omissions.

Source-boundary insufficiency must be zero before operator review.

### PD-JUNE-FM-G2 — operator blinded review

Operator-required. Freeze reviewer responses before unblinding. No answer-key access is permitted before the response hash is recorded.

### PD-JUNE-FM-WP4 — scoring and comparison

Validate the frozen response, compare with the sealed key and controls, report agreement and insufficiency by cause, and return to `PD-JUNE-FM-G3`.

### PD-JUNE-FM-G3 — reliability decision

Operator-required. Allowed decisions: `PASS`, `DEFER`, `BLOCK`, `QUARANTINE` or `SUPERSEDE`.

No result may be generalised beyond the whole-June 2026 bounded study without a separately approved plan.

## Programme-state rule

Every packet records:

`packet_id`, `plan_id`, `plan_version`, `status`, `prerequisites`, `authority_required`, `authority_delta`, `baseline_commit`, `branch`, `candidate_commit`, `tests`, `qa_packet`, `decision_record`, `merge_commit`, `blockers`, `next_packet`.

## External-artifact boundary

Raw provider objects, source CSVs, replay outputs, caches and large review payloads remain under `OVC_EXTERNAL_ARTIFACT_ROOT`. The repository stores only contracts, schemas, compact manifests, hashes, receipts, QA, decisions, tests and programme state.

## Rollback

Preserve the completed CORR2 evidence and all immutable source or review evidence. Revert only this programme's bounded contracts, tooling, compact receipts, QA, tests, workflows and state through new non-destructive commits. Never force-push, rewrite history, delete evidence, mutate selectors/releases or publish to R2.
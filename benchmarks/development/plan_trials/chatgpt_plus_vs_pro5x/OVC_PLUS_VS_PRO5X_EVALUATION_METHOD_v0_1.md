# OVC Plus → Pro 5× Development Trial — Frozen Evaluation Method v0.1

**Status:** FROZEN CANDIDATE — PENDING MAIN INTEGRATION  
**Authority effect:** NONE  
**Repository:** `owenguobadia24s-collab/ovc-replay`  
**Plus baseline:** 14 July 2026 00:00 BST through 12 August 2026 23:59:59 BST  
**Transition day:** 13 August 2026 — excluded from the primary comparison  
**Pro 5× primary window:** 14 August 2026 through 12 September 2026  
**Evaluation target:** 13 September 2026

## 1. Purpose

Freeze the repository-derived Plus baseline and comparison rules before substantive Pro 5× development accumulates. The comparison is intended to answer whether the higher ChatGPT plan materially improves OVC development quality, velocity, continuity, capacity and operator efficiency.

The subscription labels are operator-declared and are not independently verifiable from GitHub. Repository evidence is authoritative only for repository-observable development activity.

## 2. Baseline court-record boundary

The exact Plus-window UTC interval is:

`2026-07-13T23:00:00Z .. 2026-08-12T22:59:59Z`

The latest `main` commit inside that interval is:

`788dd4ea04b8df53f51369de84fff348de7c61d9`  
`C2P2-WP1: freeze core contracts and synthetic ObjectPack constitution (#685)`  
Committed `2026-08-12T22:19:18Z` / `23:19:18 BST`.

All future Plus-baseline repository analysis MUST be bounded at that SHA and time window. Later repository state may improve extraction tooling but MUST NOT move the baseline cutoff.

## 3. Repository coverage limitation

The current `ovc-replay` repository did not exist for the first five full days of the requested 30-day baseline. Its first commit is:

`b543c505a647cd7579b1d6e3af21f4ff1546ee7c` at `2026-07-19T21:55:57Z`.

Therefore 14–18 July are `NOT_OBSERVABLE_FROM_CURRENT_REPOSITORY`, not zero-development days. 19 July is only partially observable. The requested 30-day baseline remains frozen, but normalized repository metrics MUST separately disclose the 25 calendar dates on which this repository existed for at least part of the day.

No later comparison may silently convert the unavailable period into zeros.

## 4. Frozen core metrics

| Metric | Plus baseline |
|---|---:|
| PRs created in exact window | 687 |
| PRs merged in exact window | 569 |
| PRs closed unmerged in exact window | 12 |
| Closed PR dispositions | 581 |
| Merged share of closed dispositions | 97.93% |
| Main commits after initial commit through cutoff | 675 |
| Merged PRs / requested 30 calendar days | 18.97 |
| Merged PRs / repository-observable calendar date | 22.76 |

These are throughput/context measures, not equal-work-unit measures.

Secondary late-Plus maturity controls are frozen as:

- 7–12 August BST: **273 merged PRs / 6 days = 45.5/day**
- 10–12 August BST: **104 merged PRs / 3 days = 34.67/day**

They are diagnostic controls only and MUST NOT replace the primary baseline after the Pro results are known.

## 5. Comparison dimensions

The final evaluation SHALL report the following separately rather than collapse them into one unqualified score:

1. **Complexity-stratified development throughput.**
2. **Packet/PR cycle time where repository evidence can establish start and lawful completion.**
3. **Implementation/reasoning rework rate**, including corrected defects attributable to implementation or interpretation.
4. **Development-continuity proxies**, such as repeated reconciliation or restart evidence where repository records support classification.
5. **Operator-intervention proxies**, especially reserved-gate stops and manual correction/recovery events that are repository-recorded.

Raw PR volume SHALL be shown but SHALL NOT be treated as the primary productivity measure.

## 6. Frozen repository work strata

Every matched comparison should classify work into the narrowest supported stratum:

- `ADMIN_STATE_RECEIPT` — merge receipts, programme-pointer/state closeout and administrative reconciliation.
- `CONTRACT_SCHEMA_FIXTURE_REGISTRY` — deterministic contracts, schemas, registries and fixture-only packets without material runtime behavior.
- `BOUNDED_IMPLEMENTATION` — deterministic implementation plus tests within a bounded subsystem/packet.
- `INTEGRATION_ASSURANCE_CI_ORCHESTRATION` — CI, test harness, integration, head-churn, capacity, assurance or orchestration work.
- `OPERATOR_RESERVED_AUTHORITY_TRANSITION` — reserved gate/activation decisions; report separately from implementation throughput.
- `REAL_SOURCE_OR_SCIENTIFIC_EVIDENCE` — real-source replay, scientific benchmark/evidence or equivalent expensive empirical work; compare only against like work.

No scalar complexity weight is frozen in v0.1. Stratified/matched comparison is preferred to arbitrary point weighting.

## 7. Infrastructure separation

The following MUST be reported separately from model-plan performance when they materially affect cycle time:

- GitHub Actions queue/run latency;
- long replay or benchmark computation;
- provider or external-artifact latency;
- unrelated movement of `main`;
- stable-main/exact-head rerun debt;
- repository/tooling outages.

A stronger model may reduce diagnosis/recovery overhead, but it does not receive credit for infrastructure time it cannot control.

## 8. Frozen confounders

### Repository age
The Plus window starts before the current repository exists. Missing days remain `NOT_OBSERVABLE`.

### Development-orchestration maturity
DSAI and related OVC development automation/assurance matured sharply near the end of the Plus period. The Pro period starts from a stronger development stack than most of the Plus period. Final attribution MUST therefore include late-Plus controls and matched work strata.

### PR heterogeneity
OVC PRs may represent implementation, QA/evidence, gate decisions, receipts, state reconciliation or bootstrap/import work. One PR is not one equal development unit.

### Bootstrap import
PR #1 is a canonical-history import (333 changed files, 61,454 additions) and is retained as historical baseline activity but SHALL be classified as bootstrap/import rather than an ordinary work packet.

## 9. Metrics unavailable from the repository alone

The repository does not establish:

- active operator hours;
- assistant turns per packet;
- model usage-limit interruptions;
- chat-context restart count;
- subscription billing/entitlement telemetry.

If those metrics are later added from a separate trustworthy source, they MUST be labeled as a supplemental evidence plane and not silently mixed into this repository-only baseline.

## 10. Final decision rule

The 13 September evaluation should answer three distinct questions:

- **Quality:** did matched Pro work require fewer implementation/reasoning corrections or regressions?
- **Velocity:** did matched work reach lawful completion faster after separating infrastructure delay?
- **Capacity/continuity:** did materially more useful OVC work reach completion without a corresponding increase in defects or operator burden?

The result should recommend one of:

- `RETURN_TO_PLUS`
- `RETAIN_PRO_5X`
- `INSUFFICIENT_EVIDENCE_CONTINUE_TRIAL`
- `CONSIDER_PRO_20X_TRIAL`

A Pro 20× trial is justified only if Pro 5× demonstrably improves OVC productivity and 5× capacity itself becomes a material constraint. It is not justified merely by higher raw PR volume.

## 11. Non-authority statement

This benchmark changes no OVC market, scientific, semantic, selector, publication, Validation, probability, risk, exposure, execution, agent-write or governance authority. It is development-process evidence only.
